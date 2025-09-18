.PHONY: load check deploy deploy-shots logs logs-shots vercel-status

load:
	@echo "Direnv status:" && direnv status || true
	@echo "(If not allowed, run: direnv allow)"

check:
	./scripts/legend_check.sh

deploy:
	./scripts/legend_deploy.sh

deploy-shots:
	./scripts/legend_deploy.sh shots

logs:
	./scripts/legend_logs.sh api

logs-shots:
	./scripts/legend_logs.sh shots

vercel-status:
	@curl -fsS -H "Authorization: Bearer ${VERCEL_TOKEN}" \
	  "https://api.vercel.com/v6/deployments?app=legend-ai&limit=1" | jq '.deployments[0] | {state,url,createdAt}'
