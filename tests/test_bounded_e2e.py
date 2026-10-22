import copy, hashlib, io, json, sys, tempfile, threading, unittest
from email.message import Message
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from fa_mas import bounded_e2e
from fa_mas.bounded_e2e import (ROOT, Episode, Budget, BudgetStop, LiveModel, ProviderFailure,
    ScriptedModel, SYSTEM, TOOL, services, make_action as a, run_episode, load_tasks, validate_access, freeze_hash, public_model_spec)
from fa_mas.bounded_analysis import analyze
from fa_mas.preflight import review as review_preflight

P=json.loads((ROOT/'configs/bounded_e2e_v1.json').read_text())
def diagnostic(service='workflow',fault='clean'):
    return {'task_id':'diagnostic','split':'development','service':service,'fault':fault,'length':3,'requested_sku':'sku-A','capacity':2,'variant':0}

class BoundedTests(unittest.TestCase):
    def test_safe_response_shape_has_no_provider_generated_text(self):
        marker='private reasoning that must not be recorded'
        shape=bounded_e2e.safe_response_shape({'choices':[{'finish_reason':'tool_calls','message':{
            'content':'untrusted free text', 'reasoning':marker,
            'tool_calls':[{'id':'one'},{'id':'two'}]}}]})
        self.assertEqual(shape,{'finish_reason':'tool_calls','tool_call_count':2,
                                'assistant_content_present':True,'reasoning_fields_present':['reasoning']})
        self.assertNotIn(marker,json.dumps(shape))
        self.assertNotIn('untrusted free text',json.dumps(shape))

    def test_provider_error_detail_is_bounded_and_redacts_credentials(self):
        key='key_private_test_value'
        body=json.dumps({'error':{'code':'insufficient_tier','message':f'authorization Bearer {key}; api_key={key}'}}).encode()
        error=bounded_e2e.HTTPError('https://provider.example/v1/chat/completions',403,'forbidden',None,io.BytesIO(body))
        detail=bounded_e2e.provider_error_detail(error,key)
        self.assertEqual(detail,'[insufficient_tier] authorization Bearer [REDACTED]; api_key=[REDACTED]')
        headers=Message();headers['Content-Type']='text/html'
        malformed=bounded_e2e.HTTPError('https://provider.example',403,'forbidden',headers,io.BytesIO(b'<html>Forbidden</html>'))
        self.assertEqual(bounded_e2e.provider_error_detail(malformed,key),'non-JSON provider error (text/html)')

    def test_clean_workflow_and_inventory_are_model_selected_multi_step_http(self):
        with services() as bases:
            for service,actions in [('workflow',[a('invoke',1),a('invoke',2),a('invoke',3),a('finish')]),('inventory',[a('hold'),a('capture'),a('finish')])]:
                for policy in ('feature_matched','fa_mas'):
                    row=run_episode(bases[service],diagnostic(service),policy,ScriptedModel(actions),P)
                    self.assertEqual(row['task_success'],1)
                    self.assertEqual(row['tool_calls'],len(actions)-1)
                    self.assertEqual(row['evidence_class'],'ci_non_live')
                    self.assertEqual(row['model_responses'],0)
    def test_partial_workflow_requires_model_reconciliation_compensation_and_replacement(self):
        actions=[a('invoke',1),a('invoke',2),a('status',2),a('compensate',2),a('invoke',2,'alternate',True),a('invoke',3),a('finish')]
        with services() as bases:
            row=run_episode(bases['workflow'],diagnostic(fault='partial_commit'),'fa_mas',ScriptedModel(actions),P)
        self.assertEqual(row['task_success'],1);self.assertEqual(row['tool_calls'],6)
        self.assertIn('compensated',[e['status'] for e in row['state']['intents']])
    def test_contract_ablation_has_same_public_information_and_tools(self):
        task=diagnostic(fault='incompatible_alternate')
        actions=[a('invoke',1),a('invoke',2,'alternate'),a('invoke',3),a('finish')]
        with services() as bases:
            fa=Episode(bases['workflow'],task,'fa_mas',P).public_task()
            baseline=Episode(bases['workflow'],task,'feature_matched',P).public_task()
            self.assertEqual(fa,baseline);self.assertNotIn('incompatible_alternate',json.dumps(fa))
            raw=run_episode(bases['workflow'],task,'feature_matched',ScriptedModel(actions),P)
            gated=run_episode(bases['workflow'],task,'fa_mas',ScriptedModel(actions),P)
        self.assertEqual(raw['unsafe_outcome'],1)
        self.assertIn('contract_rejection',gated['events'][1]['observation'])
        self.assertEqual(gated['unsafe_outcome'],1) # prerequisite left behind; no silent cleanup
    def test_model_cleanup_can_safely_stop_and_failed_cleanup_stays_unsafe(self):
        with services() as bases:
            actions=[a('invoke',1),a('invoke',2),a('compensate',1),a('finish',reason='safe_stop')]
            row=run_episode(bases['workflow'],diagnostic(fault='incompatible_alternate'),'fa_mas',ScriptedModel(actions),P)
            self.assertEqual(row['safe_termination'],1)
            actions=[a('hold'),a('capture'),a('release'),a('finish',reason='safe_stop')]
            row=run_episode(bases['inventory'],diagnostic('inventory','capture_denied_release_unavailable'),'fa_mas',ScriptedModel(actions),P)
            self.assertEqual(row['unsafe_outcome'],1);self.assertEqual(row['safe_termination'],0)
    def test_inventory_ambiguous_reply_reconciled_by_actual_tool_loop(self):
        with services() as bases:
            row=run_episode(bases['inventory'],diagnostic('inventory','lost_after_hold'),'fa_mas',ScriptedModel([a('hold'),a('status'),a('capture'),a('finish')]),P)
        self.assertEqual(row['events'][0]['observation']['http_code'],504)
        self.assertEqual(row['task_success'],1)
    def test_inventory_compatibility_gate_is_the_only_policy_difference(self):
        actions=[a('hold',target='alternate'),a('capture'),a('finish')]
        with services() as bases:
            task=diagnostic('inventory','wrong_sku_alternate')
            baseline=run_episode(bases['inventory'],task,'feature_matched',ScriptedModel(actions),P)
            gated=run_episode(bases['inventory'],task,'fa_mas',ScriptedModel(actions),P)
        self.assertEqual(baseline['unsafe_outcome'],1)
        self.assertEqual(gated['safe_termination'],1)
    def test_provider_outage_preserves_unresolved_hold_as_unsafe(self):
        class FailingModel(ScriptedModel):
            def choose(self,messages):
                if len(messages)>2:raise ProviderFailure('diagnostic provider outage')
                return super().choose(messages)
        with services() as bases:
            row=run_episode(bases['inventory'],diagnostic('inventory'),'fa_mas',FailingModel([a('hold')]),P)
        self.assertEqual(row['status'],'provider_failure');self.assertEqual(row['unsafe_outcome'],1)
    def test_capacity_background_does_not_become_controller_unsafe_state(self):
        with services() as bases:
            row=run_episode(bases['inventory'],diagnostic('inventory','capacity_exhausted'),'fa_mas',ScriptedModel([a('hold'),a('finish',reason='safe_stop')]),P)
        self.assertEqual(row['safe_termination'],1);self.assertEqual(row['unsafe_outcome'],0)
    def test_shared_schema_rejects_unknown_actions_and_turn_limit_bounds_attempts(self):
        p=dict(P,max_turns=2)
        with services() as bases:
            row=run_episode(bases['workflow'],diagnostic(),'feature_matched',ScriptedModel([a('unknown')]*5),p)
        self.assertEqual(row['status'],'turn_limit');self.assertEqual(row['tool_calls'],0)
    def test_heldout_tasks_are_disjoint_structurally_and_never_enter_ci(self):
        dev=load_tasks(ROOT/'configs/bounded_tasks_v1.jsonl','development');held=load_tasks(ROOT/'configs/bounded_tasks_v1.jsonl','confirmatory')
        self.assertEqual(len(held),32);self.assertEqual(len(dev),4)
        self.assertFalse({t['task_id'] for t in dev}&{t['task_id'] for t in held})
        self.assertTrue(all(t['length']==2 for t in dev))
        self.assertTrue(all(t['length']>=3 for t in held))
        self.assertTrue(all(t['requested_sku']!='sku-A' for t in held))
    def test_budget_reservation_limits_and_access_cannot_freeze_placeholders(self):
        spec={'input_usd_per_million':10,'output_usd_per_million':10}
        b=Budget(1,1,[spec]);b.reserve(spec,P)
        with self.assertRaises(BudgetStop):b.reserve(spec,P)
        with self.assertRaises(ValueError):validate_access(json.loads((ROOT/'configs/bounded_access.example.json').read_text()))
    def test_request_options_are_limited_to_frozen_provider_controls(self):
        valid={'models':[
            {'class':'hosted','model_id':'hosted-snapshot','base_url':'https://host.example/v1','api_key_env':'HOSTED_API_KEY','input_usd_per_million':1,'output_usd_per_million':1,'output_token_parameter':'max_completion_tokens','request_options':{'reasoning_effort':'none','parallel_tool_calls':False},'preserve_reasoning_fields':False,'byte_token_upper_bound_verified':True,'output_billing_ceiling_verified':True},
            {'class':'open_weight','model_id':'open-weight-revision','base_url':'https://open.example/v1','api_key_env':'OPEN_WEIGHT_API_KEY','input_usd_per_million':1,'output_usd_per_million':1,'output_token_parameter':'max_tokens','request_options':{},'preserve_reasoning_fields':True,'assistant_tool_content':'empty_string','byte_token_upper_bound_verified':True,'output_billing_ceiling_verified':True}
        ]}
        validate_access(valid)
        self.assertEqual(public_model_spec(valid['models'][0])['request_options']['reasoning_effort'],'none')
        self.assertEqual(public_model_spec(valid['models'][1])['assistant_tool_content'],'empty_string')
        valid['models'][1]['request_options']={'model':'replacement'}
        with self.assertRaises(ValueError):validate_access(valid)
        valid['models'][1]['request_options']={};valid['models'][1]['preserve_reasoning_fields']='yes'
        with self.assertRaises(ValueError):validate_access(valid)
        valid['models'][1]['preserve_reasoning_fields']=True;valid['models'][1]['assistant_tool_content']='null'
        with self.assertRaises(ValueError):validate_access(valid)
    def test_development_access_permits_pending_confirmatory_billing_guarantees(self):
        access={'models':[
            {'class':'hosted','model_id':'hosted-snapshot','base_url':'https://host.example/v1','api_key_env':'HOSTED_API_KEY','input_usd_per_million':1,'output_usd_per_million':1,'output_token_parameter':'max_completion_tokens','temperature':None,'request_options':{},'byte_token_upper_bound_verified':False,'output_billing_ceiling_verified':False},
            {'class':'open_weight','model_id':'open-weight-revision','base_url':'https://open.example/v1','api_key_env':'OPEN_WEIGHT_API_KEY','input_usd_per_million':1,'output_usd_per_million':1,'output_token_parameter':'max_tokens','temperature':0,'request_options':{},'byte_token_upper_bound_verified':False,'output_billing_ceiling_verified':False}
        ]}
        validate_access(access,require_confirmatory_guarantees=False)
        with self.assertRaises(ValueError):validate_access(access)
    def test_live_development_mode_is_bounded_and_cannot_create_confirmatory_evidence(self):
        received=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));received.append(body)
                task=json.loads(body['messages'][1]['content']);turn=sum(m['role']=='tool' for m in body['messages'])
                actions=([a('invoke',1),a('status',1),a('invoke',2),a('finish')]
                         if task['catalog']['service']=='workflow' else [a('hold'),a('status'),a('capture'),a('finish')])
                action=actions[min(turn,len(actions)-1)]
                payload=json.dumps({'id':'development-mock-'+str(len(received)),'model':body['model'],
                    'usage':{'prompt_tokens':40,'completion_tokens':20},
                    'choices':[{'message':{'content':None,'tool_calls':[{'id':'provider-'+str(len(received)),'type':'function','function':{'name':'execute_service_action','arguments':json.dumps(action)}}]}}]}).encode()
                self.send_response(200);self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.02},daemon=True);thread.start()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp);protocol=path/'protocol.json';tasks=path/'tasks.jsonl';access=path/'access.json';output=path/'development'
                protocol.write_text((ROOT/'configs/bounded_e2e_v1.json').read_text());tasks.write_text((ROOT/'configs/bounded_tasks_v1.jsonl').read_text())
                base=f'http://127.0.0.1:{server.server_address[1]}/v1'
                access.write_text(json.dumps({'models':[
                    {'class':'hosted','model_id':'hosted-development-mock','expected_response_model':'hosted-development-mock','base_url':base,'api_key_env':'UNSET_HOSTED_KEY','input_usd_per_million':0,'output_usd_per_million':0,'output_token_parameter':'max_completion_tokens','temperature':None,'request_options':{'reasoning_effort':'none'},'byte_token_upper_bound_verified':False,'output_billing_ceiling_verified':False},
                    {'class':'open_weight','model_id':'open-development-mock','expected_response_model':'open-development-mock','base_url':base,'api_key_env':'UNSET_OPEN_KEY','input_usd_per_million':0,'output_usd_per_million':0,'output_token_parameter':'max_tokens','temperature':0,'request_options':{'parallel_tool_calls':False},'byte_token_upper_bound_verified':False,'output_billing_ceiling_verified':False}
                ]}))
                argv=['bounded_e2e','--mode','development','--protocol',str(protocol),'--tasks',str(tasks),'--access',str(access),'--approve-spend-usd','1','--output',str(output)]
                with patch.object(sys,'argv',argv):bounded_e2e.main()
                manifest=json.loads((output/'development_live_manifest.json').read_text())
                rows=[json.loads(line) for line in (output/'development_live_runs.jsonl').read_text().splitlines()]
                self.assertEqual(manifest['evidence_class'],'live_development_local_services')
                self.assertEqual((manifest['planned_episodes'],manifest['launched_episodes']),(16,16))
                self.assertTrue(all(row['evidence_class']=='live_development_local_services' for row in rows))
                self.assertFalse((path/'bounded_e2e_execution_started.json').exists())
                with self.assertRaises(ValueError):analyze(output/'development_live_runs.jsonl',output/'development_live_manifest.json',tasks,path/'analysis')
        finally:server.shutdown();server.server_close();thread.join()
        hosted=next(body for body in received if body['model']=='hosted-development-mock')
        open_weight=next(body for body in received if body['model']=='open-development-mock')
        self.assertNotIn('temperature',hosted);self.assertEqual(hosted['reasoning_effort'],'none')
        self.assertEqual(open_weight['temperature'],0);self.assertFalse(open_weight['parallel_tool_calls'])
    def test_single_openai_configuration_requires_a_passed_preflight_before_freeze(self):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                task=json.loads(body['messages'][1]['content']);turn=sum(m['role']=='tool' for m in body['messages'])
                if task['catalog']['service']=='workflow':
                    actions=[a('invoke',step) for step in task['catalog']['steps']]+[a('finish')]
                else:
                    actions=[a('hold'),a('capture'),a('finish')]
                action=actions[min(turn,len(actions)-1)]
                payload=json.dumps({'id':'openai-single-mock-'+str(turn),'model':body['model'],
                    'usage':{'prompt_tokens':40,'completion_tokens':20},
                    'choices':[{'message':{'content':None,'tool_calls':[{'id':'call-'+str(turn),'type':'function','function':{'name':'execute_service_action','arguments':json.dumps(action)}}]}}]}).encode()
                self.send_response(200);self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.02},daemon=True);thread.start()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp);protocol=path/'protocol.json';tasks=path/'tasks.jsonl';access=path/'access.json';development=path/'development';live=path/'live';report=development/'preflight_report.json'
                protocol.write_text((ROOT/'configs/openai_single_e2e_v1.json').read_text());tasks.write_text((ROOT/'configs/bounded_tasks_v1.jsonl').read_text())
                config=json.loads((ROOT/'configs/openai_luna_preflight.json').read_text())
                model=config['models'][0];model['base_url']=f'http://127.0.0.1:{server.server_address[1]}/v1';model['input_usd_per_million']=0;model['output_usd_per_million']=0
                access.write_text(json.dumps(config))
                argv=['bounded_e2e','--mode','development','--protocol',str(protocol),'--tasks',str(tasks),'--access',str(access),'--approve-spend-usd','1','--output',str(development)]
                with patch.object(sys,'argv',argv):bounded_e2e.main()
                manifest=development/'development_live_manifest.json';runs=development/'development_live_runs.jsonl'
                checked=review_preflight(protocol,tasks,access,runs,manifest,report)
                self.assertEqual(checked['status'],'passed')
                self.assertEqual((checked['planned_episodes'],checked['observed_episodes']),(8,8))
                argv=['bounded_e2e','--mode','freeze','--protocol',str(protocol),'--tasks',str(tasks),'--access',str(access)]
                with patch.object(sys,'argv',argv):
                    with self.assertRaises(ValueError):bounded_e2e.main()
                malformed=dict(checked);malformed['observed_episodes']=7;bad_report=development/'malformed_preflight_report.json';bad_report.write_text(json.dumps(malformed))
                argv.extend(['--preflight-report',str(bad_report)])
                with patch.object(sys,'argv',argv):
                    with self.assertRaises(ValueError):bounded_e2e.main()
                argv=argv[:-2]
                argv.extend(['--preflight-report',str(report)])
                with patch.object(sys,'argv',argv):bounded_e2e.main()
                lock=protocol.with_name(protocol.stem+'_lock.json');self.assertTrue(lock.exists())
                argv=['bounded_e2e','--mode','live','--protocol',str(protocol),'--tasks',str(tasks),'--access',str(access),'--approve-spend-usd','1','--output',str(live)]
                with patch.object(sys,'argv',argv):bounded_e2e.main()
                result=analyze(live/'live_runs.jsonl',live/'live_manifest.json',tasks,path/'analysis')
                self.assertEqual(result,{'rows':64,'clusters':16,'evidence_class':'live_e2e_local_services'})
        finally:server.shutdown();server.server_close();thread.join()
    def test_non_live_analysis_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp);(path/'m.json').write_text('{"evidence_class":"ci_non_live"}')
            with self.assertRaises(ValueError):analyze(path/'runs',path/'m.json',ROOT/'configs/bounded_tasks_v1.jsonl',path/'out')
    def test_model_wire_protocol_multi_turn_preserves_tool_observations_non_live(self):
        received=[];actions=[a('hold'),a('status'),a('capture'),a('finish')]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                received.append((body,{key.lower():value for key,value in self.headers.items()}))
                action=actions[len(received)-1]
                payload=json.dumps({'id':str(len(received)),'model':'mock-only','usage':{'prompt_tokens':40,'completion_tokens':20},
                    'choices':[{'message':{'content':None,'reasoning':'opaque test rationale','tool_calls':[{'id':'provider-call-'+str(len(received)),'type':'function','function':{'name':'execute_service_action','arguments':json.dumps(action)}}]}}]}).encode()
                self.send_response(200);self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.02},daemon=True);thread.start()
        spec={'model_id':'mock-only','class':'test','base_url':f'http://127.0.0.1:{server.server_address[1]}/v1','api_key_env':'UNSET_DIAGNOSTIC_KEY','input_usd_per_million':0,'output_usd_per_million':0,'request_options':{'reasoning_effort':'none','parallel_tool_calls':False},'preserve_reasoning_fields':True,'assistant_tool_content':'empty_string'}
        class NonLiveWireModel(LiveModel):is_live=False
        model=NonLiveWireModel(spec,P,Budget(12,1,[spec]))
        try:
            with services() as bases:
                row=run_episode(bases['inventory'],diagnostic('inventory','lost_after_hold'),'fa_mas',model,P)
        finally:server.shutdown();server.server_close();thread.join()
        self.assertEqual(row['task_success'],1);self.assertEqual(row['evidence_class'],'ci_non_live')
        self.assertEqual(len(received),4);self.assertEqual(len(received[-1][0]['messages']),8)
        self.assertEqual(received[1][0]['messages'][-1]['role'],'tool')
        self.assertIn('504',received[1][0]['messages'][-1]['content'])
        self.assertEqual(row['total_tokens'],240)
        self.assertEqual(received[0][0]['max_tokens'],P['max_output_tokens'])
        self.assertEqual(received[0][0]['reasoning_effort'],'none')
        self.assertFalse(received[0][0]['parallel_tool_calls'])
        self.assertEqual(received[0][1]['accept'],'application/json')
        self.assertEqual(received[0][1]['user-agent'],'FA-MAS-Live-Evaluation/1.0')
        self.assertEqual(received[1][0]['messages'][-2]['tool_calls'][0]['id'],'provider-call-1')
        self.assertEqual(received[1][0]['messages'][-1]['tool_call_id'],'provider-call-1')
        self.assertEqual(received[1][0]['messages'][-2]['content'],'')
        self.assertEqual(received[1][0]['messages'][-2]['reasoning'],'opaque test rationale')
        self.assertNotIn('reasoning',row['events'][0]['model'])
        self.assertNotIn('assistant_content',row['events'][0]['model'])
        self.assertEqual(row['events'][0]['model']['response_shape'],
                         {'finish_reason':None,'tool_call_count':1,
                          'assistant_content_present':False,'reasoning_fields_present':['reasoning']})
        self.assertNotIn('opaque test rationale',json.dumps(row['events']))
    def test_lock_changes_if_any_service_code_or_access_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);access=p/'access.json';access.write_text('{"diagnostic":1}')
            h1=freeze_hash(ROOT/'configs/bounded_e2e_v1.json',ROOT/'configs/bounded_tasks_v1.jsonl',access)
            access.write_text('{"diagnostic":2}')
            h2=freeze_hash(ROOT/'configs/bounded_e2e_v1.json',ROOT/'configs/bounded_tasks_v1.jsonl',access)
        self.assertNotEqual(h1,h2)
