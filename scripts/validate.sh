#!/usr/bin/env bash
set -e
cd "$(dirname "$0")" || exit 1
echo "== kubectl kustomize render =="
if kubectl kustomize k8s/base > /tmp/rendered.yaml 2>/tmp/rendered.err; then
  docs=$(grep -c '^kind:' /tmp/rendered.yaml || true)
  echo "RENDER OK (${docs} docs)"
else
  echo "RENDER FAIL:"
  cat /tmp/rendered.err
  exit 1
fi
echo "== per-kind counts =="
grep '^kind:' /tmp/rendered.yaml | sort | uniq -c
echo "== docker-compose.display.yml validate =="
if docker compose -f docker-compose.display.yml config >/dev/null 2>/tmp/disp.err; then
  echo "DISPLAY COMPOSE OK"
else
  echo "DISPLAY COMPOSE FAIL:"; cat /tmp/disp.err
fi
