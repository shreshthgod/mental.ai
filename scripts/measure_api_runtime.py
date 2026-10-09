"""Isolated synthetic ASGI/model latency experiment, provider transport stub.

No deployed network, real identities/disclosures, clinical score or multi-worker
claim. This is concurrent actual inference through the authenticated route.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import resource
import sys
import tempfile
import time


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--concurrency',type=int,default=4,choices=range(1,9))
    parser.add_argument('--requests',type=int,default=24,choices=range(1,25))
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    sys.path.insert(0,str(root/'tests'))
    sys.path.insert(0,str(root/'Step 12 - Packaging/package'))
    sys.path.insert(0,str(root))
    from _supabase_stub import StubSupabase, install
    from api import db
    install(StubSupabase())
    start=time.perf_counter()
    from api import api as service
    cold_import_ms=(time.perf_counter()-start)*1000
    from fastapi.testclient import TestClient
    from api.limits import PredictLimiter
    from scripts.source_fingerprint import fingerprint
    with tempfile.TemporaryDirectory(prefix='mental-ai-latency-') as isolated:
        service.predict_limiter=PredictLimiter(str(Path(isolated)/'limits.sqlite3'))
        with TestClient(service.app) as client:
            token=client.post('/auth/login',json={'user_id':'alice@example.com','password':'alice-pass'}).json()['token']
            def predict(index):
                started=time.perf_counter()
                response=client.post('/predict',headers={'Authorization':'Bearer '+token},
                    json={'text':'i wanna jump from 10th floor'})
                result=response.json()
                return {'index':index,'latency_ms':(time.perf_counter()-started)*1000,
                    'status':response.status_code,'request_id':result.get('request_id'),
                    'level':result.get('safety',{}).get('level'),
                    'save':result.get('persistence',{}).get('status')}
            cold=predict(-1)
            batch_start=time.perf_counter()
            with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
                observations=list(pool.map(predict,range(args.requests)))
            batch_seconds=time.perf_counter()-batch_start
    db.reset_client()
    latencies=sorted(r['latency_ms'] for r in observations)
    quantile=lambda p:latencies[int((len(latencies)-1)*p)]
    report={'run_id_utc':datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'),
        'layer':'authenticated in-process ASGI + actual models; GoTrue/PostgREST transport stub',
        'runtime':platform.python_version(),'machine':platform.machine(),'system':platform.system(),
        'cpu_count':os.cpu_count(),'concurrency':args.concurrency,'samples':args.requests,
        'processes':1,'inference_workers':1,'admission_limit':8,
        'cold_import_ms':cold_import_ms,'cold_first_prediction':cold,
        'warm_quantile_method':'sorted floor index: int((n-1)*p)',
        'warm_p50_ms':quantile(.5),'warm_p95_ms':quantile(.95),'warm_p99_ms':quantile(.99),
        'batch_seconds':batch_seconds,'errors':sum(r['status']!=200 for r in observations),
        'timeouts':sum(r['status']==503 for r in observations),
        'peak_process_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'source_fingerprint':fingerprint(root),'observations':observations,
        'limitations':'Small synthetic one-process experiment, not deployed/multi-worker/provider latency or clinical validation.'}
    path=root/'reports'/f"runtime-asgi-{report['run_id_utc']}.json"
    path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in {'source_fingerprint','observations'}}))
    print('report:',path.relative_to(root))
    return 0 if report['errors']==0 and all(r['level']=='HIGH' for r in observations) else 1


if __name__=='__main__':
    raise SystemExit(main())
