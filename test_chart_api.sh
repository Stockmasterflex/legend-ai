#!/bin/bash

API_BASE="https://legend-api.onrender.com"
SYMBOL="AAPL"

echo "🔍 Testing Chart API Integration"
echo "==============================="
echo ""
echo "Testing chart API endpoint with symbol=$SYMBOL"

response=$(curl -s "$API_BASE/api/v1/chart?symbol=$SYMBOL")
echo ""
echo "Response from API:"
echo "$response" | jq .

chart_url=$(echo "$response" | jq -r '.chart_url')

if [[ $chart_url == "null" || $chart_url == "" ]]; then
  echo "❌ No chart_url in response!"
else
  echo "✅ Found chart_url: $chart_url"
  echo "Testing URL accessibility..."
  status_code=$(curl -s -o /dev/null -w "%{http_code}" "$chart_url")
  if [[ $status_code == "200" ]]; then
    echo "✅ Chart URL is accessible (HTTP 200)"
  else
    echo "❌ Chart URL returned HTTP $status_code"
  fi
fi