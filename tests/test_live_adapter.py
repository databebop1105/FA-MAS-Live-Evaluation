import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from fa_mas.live_tier import OpenAICompatibleAdapter, validate_config

class AdapterTests(unittest.TestCase):
    def test_tool_call_wire_protocol_is_non_live_mock(self):
        requests=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_POST(self):
                body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                requests.append((self.path,body))
                payload=json.dumps({'id':'mock-only','choices':[{'message':{'tool_calls':[{'function':{'arguments':'{"action":"reconcile","target":"failed_step","confidence":0.7}'}}]}}],'usage':{'total_tokens':9}}).encode()
                self.send_response(200); self.send_header('Content-Length',str(len(payload))); self.end_headers(); self.wfile.write(payload)
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            adapter=OpenAICompatibleAdapter('mock-tool-model',f'http://127.0.0.1:{server.server_address[1]}','UNSET_TEST_KEY','hosted')
            result=adapter.choose('test',['reconcile','abstain'],0)
        finally:server.shutdown();server.server_close();thread.join()
        self.assertEqual(requests[0][0],'/v1/chat/completions')
        self.assertEqual(requests[0][1]['model'],'mock-tool-model')
        self.assertEqual(result['action'],'reconcile')
        self.assertEqual(result['usage']['total_tokens'],9)
    def test_freeze_requires_pinned_endpoint(self):
        base={'protocol_version':'live-tier-v1','confirmatory_split':'confirmatory','models':[
            {'class':'hosted','model_id':'exact','base_url':'${HOSTED_BASE_URL}'},
            {'class':'open_weight','model_id':'exact','base_url':'http://localhost:8000'}]}
        with self.assertRaises(ValueError):validate_config(base)
        base['models'][0]['base_url']='http://example.org'
        with self.assertRaises(ValueError):validate_config(base)
        base['models'][0]['base_url']='https://example.org'
        validate_config(base)
