import argparse, json, sys
from core.orchestrator.router import ModelRouter
from core.orchestrator.policies import Policy
from core.orchestrator.tools import ToolRegistry

reg = ToolRegistry()
reg.register('echo', lambda p: { 'ok': True, 'payload': p })
router = ModelRouter(config={"preference": "local_first", "allow_ollama": True, "allow_relay": True, "max_latency_ms": 1500})
policy = Policy(name="default")

parser = argparse.ArgumentParser(description='Sheratan CLI')
sub = parser.add_subparsers(dest='cmd')

# decide
pp = sub.add_parser('decide', help='Router decision for a job JSON')
pp.add_argument('--job', type=str, help='Inline JSON for job', required=False)
pp.add_argument('--file', type=str, help='Path to job.json', required=False)

# tool
tp = sub.add_parser('tool', help='Run a registered tool')
tp.add_argument('--name', required=True)
tp.add_argument('--payload', required=False, default='{}')

args = parser.parse_args()

if args.cmd == 'decide':
    data = json.loads(args.job) if args.job else json.load(open(args.file,'r',encoding='utf-8'))
    if not policy.allow(data):
        print(json.dumps({"decision": None, "reason": "policy_reject"}))
        sys.exit(0)
    d = router.choose(data)
    print(json.dumps({"decision": d.model, "reason": d.reason, "policy": d.policy}))
elif args.cmd == 'tool':
    payload = json.loads(args.payload)
    print(json.dumps(reg.run(args.name, payload)))
else:
    parser.print_help()
