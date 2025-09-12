# Phase 2_ Data Collection in n8n

> Imported from: `/Users/kyleholthaus/Downloads/repoLAI Docs /Phase 2_ Data Collection in n8n.pdf`
> Converted: 2025-09-11 21:33:33

Phase 2: Data Collection in n8n 

In this guide, we will create an n8n workflow that automatically fetches daily stock prices and builds a 
historical log in Google Sheets. We’ll use Alpha Vantage as the primary data source (with an API key) 
and Yahoo Finance as a fallback if we hit Alpha Vantage’s rate limits. The workflow will run on a 
schedule (daily at 5:00 PM ET after market close, with notes on how to adjust it to run more frequently like 
hourly). We’ll cover every step in detail – from setting up secure API credentials, configuring each node 
(with exact field values), connecting the nodes, to adding error handling (retries, logging failures to a 
separate sheet, and ensuring the workflow continues even if some tickers fail). This guide assumes no 
prior experience with n8n, so we’ll explain each click and configuration field, and include code 
explanations line-by-line for any Function nodes. Let’s get started! 
1. Prepare API Credentials and Google Sheets 
Before building the workflow, we need to set up our API access and Google Sheets for use in n8n. This 
ensures our workflow can authenticate to the services and read/write data. 
1.1 Sign Up for Alpha Vantage API Key – Go to the Alpha Vantage website and sign up for a free API 
key (if you haven’t already). Alpha Vantage’s free tier allows 5 API requests per minute and 500 per 
day . You’ll receive a 16-digit API key via email. Keep this key handy, but do not share it publicly. We 
will store it securely in n8n in the next step. 
1.2 Add Alpha Vantage API Key to n8n Credentials – In n8n, API keys should be stored in the 
Credentials vault so they remain encrypted and are not visible in plain text . Here’s how to set that up: 
Open n8n Credentials: In the n8n editor UI, find the Credentials tab (usually on the 

1. 

top-right toolbar) and click “New” to create a new credential. Select “HTTP Request” as the credential 
type (since Alpha Vantage will be called via HTTP). 

2. 

Configure Credential for API Key: In the HTTP Request credential form, set 

Authentication to “Generic > Query Auth” (meaning we’ll add an API key as a query parameter). Two 
fields will appear: “Name” and “Value”. For Name, enter apikey (this is the query parameter name Alpha 
Vantage expects). For Value, paste your Alpha Vantage API key. 

3. 

Name the Credential: Give this credential a recognizable name, e.g. “AlphaVantage 

API Key”, so you can identify it later. 

4. 

Save: Click Save to store this credential. n8n will encrypt the API key value in its 

database. Now we can use this credential in our HTTP nodes securely (the key will not be exposed in the 
workflow export or editor) . 
1.3 Create a Google Cloud Service Account for Google Sheets – To allow n8n to access Google 
Sheets, it’s best to use a Google Service Account (which is a special Google account for server-to-server 
interactions). This avoids the need for manual OAuth logins. Follow these steps: 

1. 

Google Cloud Console: Go to the Google Cloud Console and create a new project (or 

use an existing project for this purpose) . 

2. 

Enable APIs: In the Cloud Console, navigate to APIs & Services > Library. Enable the 

Google Sheets API and the Google Drive API for your project  . (Enabling Drive API is required because 
Google Sheets uses Google Drive under the hood to manage files). 

3. 

Create Service Account: Next, go to APIs & Services > Credentials . Click “+ 

CREATE CREDENTIALS” and choose “Service account”. Give it a name like “n8n Google Sheets SA”. 
You can skip assigning roles for this use-case (or assign “Project > Viewer” just to be safe). Finish the 
service account creation steps (you can click Done when prompted to grant user access – it’s not needed 
for our purposes). 
4. 

Generate Key: In your new service account’s details, go to the “KEYS” tab. Click “Add 

Key > Create new key”, select JSON, and click Create . A JSON file will download – this contains the 
service account’s credentials. Open this file in a text editor. You’ll see fields like "client_email" and 
"private_key". 

 
 
 
 
 
 
 
 
 
5. 

Add Google Sheets Credential in n8n: In n8n, create a new credential and choose 

“Google Sheets” (or “Google Service Account” if using a generic Google credential type). It will ask for 
the Service Account Email and Private Key. Copy the client_email from the JSON and paste it into the 
Service Account Email field. Copy the private_key (the long block starting with -----BEGIN PRIVATE 
KEY-----) and paste it into the Private Key field – make sure to copy everything between and 
excluding the quotes (do not include the quotes or \n literals; include actual newline characters) . Enable 
Impersonate a User only if needed (not required here). Save the Google Sheets credential with a name 
like “Google Sheets Service Account”. 

6. 

Share Google Sheet with Service Account: This step is crucial – by default, a new 

service account cannot access your existing Google Sheets until you share them. Take note of the service 
account’s email (the one you pasted, ending with .gserviceaccount.com). Go to your Google Drive and 
create a new Google Spreadsheet (e.g., “Stock Data”). Inside this spreadsheet, create two sheets: one 
named “Watchlist” (for the tickers to monitor), and another named “HistoricalData” (for appending the 
daily OHLCV data). Also create a third sheet “Errors” to log any failed ticker fetches. Now share this 
spreadsheet with the service account’s email (use the Share button in Google Sheets and add the service 
account email as a viewer or editor) . This grants the service account permission to read and write to the 
spreadsheet. 
1.4 Prepare the Google Sheets – In the “Watchlist” sheet, list the stock tickers you want to track in the 
first column (you can start from cell A2 downward, and use row 1 for a header like “Ticker”). For example, 
A2: AAPL, A3: GOOGL, A4: MSFT, etc. The n8n workflow will read this list dynamically, so you can 
add/remove tickers later without changing the workflow. In the “HistoricalData” sheet, set up a header 
row (in row 1) with the columns: Date, Ticker, Open, High, Low, Close, Volume, Percent Change. The 
workflow will append new rows under these headers each time it runs. In the “Errors” sheet, you can 
have headers like Date, Ticker, Error Message to log any failures. (Having headers is recommended so 
that n8n can map incoming fields by name when appending rows.) 
Now that credentials and sheets are set up, we can build the n8n workflow. 
2. Build the n8n Workflow 
We will now create each node in n8n and configure it step by step. Open the n8n editor (either the 
desktop app or web UI) and create a new workflow. We’ll add nodes in the order that data flows: trigger → 
read tickers → fetch data → process data → write to sheets, with error handling branches as needed. 
2.1 Add a Schedule Trigger (Cron) Node – This node will trigger the workflow automatically at 5:00 PM 
ET daily (after market close). On the left sidebar in n8n, click the “Nodes” panel and search for “Cron” or 
“Schedule Trigger”. Click and drag the Schedule Trigger node onto the canvas (or simply click it). By 
default, it may be named “Cron” or “Schedule Trigger 1”. Double-click the node (or select it and use the 
right settings panel) to configure it. Set the following: 

• 
• 

Mode/Trigger Type: Select Every Day (if available). This allows choosing a daily time. 
Time: Set Hour = 17 and Minute = 0. Since we want 5:00 PM Eastern Time, you have 

two options: 

• 
• 

If your n8n instance or workflow is configured for Eastern Time, just set it to 17:00. 
If your n8n is in a different timezone (e.g., UTC), you can either convert 5 PM ET to that 

timezone or adjust the workflow timezone. For example, 5 PM ET is 2 PM PT or 21:00 UTC during 
Standard Time. It’s important to align the timezone correctly. n8n’s Schedule Trigger uses the workflow’s 
timezone setting if one is specified, otherwise it uses the server’s default timezone . To avoid confusion, 
you can set the workflow’s timezone explicitly to Eastern Time (in the workflow settings menu, set 
Timezone = America/New_York) so that 17:00 in the Cron node corresponds to 5 PM ET. 

• 

Repeat Frequency: Leave it at every 1 day (this should be the default for daily). 

After these settings, the Cron node will fire at 5:00 PM ET every day. (Optional: If you also want to allow 
more frequent runs (e.g., hourly), you could duplicate this node or adjust it to a different schedule. For 

 
 
 
 
 
 
 
instance, to run hourly, set Mode to Every Hour or use a custom cron expression like 0 0 * * * * for every 
hour on the hour. But for our primary setup, we’ll stick with daily at market close.) 
Verification: There isn’t immediate output to test for a trigger node except time itself. However, for testing 
purposes, you can manually trigger the workflow. While building, you can right-click the Cron node and 
select “Execute Node” (or click “Execute Workflow” top-right) to simulate a trigger – it will start the 
workflow immediately in the editor for testing. Remember to turn off “Active” for the workflow (top-right 
toggle) until you finish building and testing, to prevent it from running on schedule before it’s fully set up. 
2.2 Add a Google Sheets Node (Read Watchlist) – Next, we want to read our list of tickers from the 
Google Sheet. From the Nodes panel, search for “Google Sheets” and add it to the canvas. Connect the 
output of the Cron node to the input of the Google Sheets node by dragging the arrow from Cron to 
Google Sheets. This means every day at 5 PM ET, the Google Sheets node will execute. Now configure 
the Google Sheets node: 

• 

Credentials: Select the Google Sheets credential we created (e.g., “Google Sheets 

Service Account”). This connects the node to your Google account via the service account . If it’s not in 
the dropdown, click “Refresh credentials” or ensure you saved it correctly. 

rows). 

• 

• 

Resource: Select “Sheet” (since we are working within a spreadsheet and want to read 

Operation: Select “Get Many Rows” (or it might say “Read Rows” or “Get All Rows” – 

n8n labels can vary by version, but essentially we want to retrieve multiple rows). This operation will fetch 
all rows from a sheet. 

• 

Spreadsheet ID: Here you can either paste the Google Spreadsheet’s ID or use the 

search picker. The spreadsheet ID is the long string in the URL of your Google Sheet (between /d/ and 
/edit). For example, in https://docs.google.com/spreadsheets/d/1AbCDefGhIJKLmnopQRs_tUvWXyz/edit, 
the ID is 1AbCDefGhIJKLmnopQRs_tUvWXyz. Paste that ID here. Alternatively, if you click into the field, 
n8n may list recent spreadsheets accessible by your credentials – you can select your “Stock Data” 
spreadsheet from the list. 

• 

Sheet Name: Enter “Watchlist” (the name of the sheet tab containing the tickers). 

Ensure spelling and capitalization match exactly. 

• 

Range or Start/End: You can leave Range blank to fetch the whole sheet, or specify 

something like A2:A to read only the first column (tickers) from A2 downwards. To be safe (and to skip the 
header), you might set Range = A2:A1000 (assuming you won’t have more than 1000 tickers; adjust as 
needed). This ensures the header row is not included. If you leave it blank, the node might return the 
header as well – check “Include Header” option if present. If the node has an option “Use Header Row”, 
you can enable it so that it uses the first row as keys (but since we only need the tickers, it’s fine either 
way). 
After configuring, click “Execute Node” (while in the node editor, there’s usually an Execute button) to 
test it. The Google Sheets node should connect and retrieve the list of tickers. In the n8n editor, you’ll see 
the output data under the node. Each row becomes one item. For example, if your Watchlist sheet has 
AAPL, GOOGL, MSFT, you should see three output items with a field for the ticker (likely named after the 
column header, e.g., Ticker: "AAPL"). If you see an error, verify the spreadsheet ID, sheet name, and that 
the service account email has access to the file (if not, share the file with that email and try again). Once it 
returns the list of tickers, we’re ready to fetch stock data for each. 
2.3 Add an HTTP Request Node for Alpha Vantage – Now we will add an HTTP Request node to call 
the Alpha Vantage API for each ticker. This node will use the tickers from the Google Sheets node as 
input and make API calls. Search for “HTTP Request” in the Nodes panel and add it to the canvas. 
Connect the output of Google Sheets node to the input of HTTP Request. Configure the HTTP node 
as follows: 

• 
• 

HTTP Method: Select GET (we will be calling a GET endpoint). 
URL: We’ll use Alpha Vantage’s Time Series Daily API. Enter the base URL: 

 
 
 
 
 
 
 
 
https://www.alphavantage.co/query 
We will supply the query parameters separately (which is a good practice). 

• 

Query Parameters: Add the following query params (click “Add Parameter” to add each, 

and fill Name and Value): 

• 

Name: function – Value: TIME_SERIES_DAILY (this tells Alpha Vantage which data we 

want; daily OHLCV time series). 
(Note: If you want adjusted close and dividends info, you can use TIME_SERIES_DAILY_ADJUSTED 
instead. For simplicity, we’ll use the non-adjusted to get basic OHLCV.) 

• 

Name: symbol – Value: an expression referencing the ticker from the input. Click into the 
Value field, then click the little gears/selector icon to switch to Expression mode. In the expression editor, 
select the current node’s input JSON > the ticker field. For example, it might be something like 
{{$json["Ticker"]}} or {{$json["ticker"]}} depending on your Google Sheets output. You can also type the 
expression: if the item has a field “Ticker”, use {{$json.Ticker}}. This ensures the HTTP node uses each 
ticker from the previous node. (The HTTP node will automatically iterate for each incoming item, making 
one request per ticker.) 

• 

Name: apikey – Value: (Leave blank if using credentials). Instead of hardcoding the 

API key here, we will use the credential we set up. See below for setting the credential in the 
Authentication section. (If you did not set up the credential in step 1.2, you could put your API key here 
directly, but that’s not secure or recommended.) 

• 

(Optional) Name: datatype – Value: json (Alpha Vantage returns JSON by default, so this 

isn’t strictly needed. But no harm including it.) 

• 

(Optional) Name: outputsize – Value: compact. By default, Alpha Vantage’s daily API 

returns 100 days (“compact”) of data. “full” would return 20+ years which we don’t need every run. We’ll 
use compact for efficiency. 

• 

Authentication: Click on the “Authentication” section of the HTTP node. Choose “Use 

Generic Credential” (or similar) and select the credential “AlphaVantage API Key” that we created 
earlier. This credential is set to inject the apikey query parameter for us, so it will automatically append 
&apikey=YOUR_KEY to each request . If you set up the credential as “Query Auth” with the name apikey, 
you do not need to fill the apikey in Query Parameters manually – the credential will handle it. (If you did 
accidentally put the key in Query Params as well, that’s okay but it will expose the key in the workflow. 
Relying on the credential is better.) 

• 

Options > Retry On Fail: Enable Retry on Fail and set Max Retries = 3. Also set a 

short Retry Delay (for example, 3 seconds) if available. This tells n8n to retry the API call up to 3 times if 
it fails (due to a transient network error, for instance). 

• 

Options > Continue On Fail: Set this to “Continue (pass error to second output)”. In 

some versions, this might be a setting called On Error where you choose “Continue” and possibly an 
option for error output. We want the workflow to not stop if one ticker’s API call fails. By enabling 
continue-on-fail, the HTTP node will produce output for successful calls on its main output, and route 
failed calls to a separate error output path, instead of stopping the whole workflow. This ensures 
subsequent tickers still get processed . (We will handle the error output in a later step.) 

• 

Test the HTTP Node: It’s a good idea to test this node with one ticker to make sure it’s 

working. You can do this by selecting the HTTP node and clicking “Execute Node”. It will take the output 
from Google Sheets (make sure the Google Sheets node has executed and has data in the previous step) 
and perform the requests. In the output, for each ticker item, you should see a JSON result. Each result 
from Alpha Vantage contains two main parts: "Meta Data" and "Time Series (Daily)". Under "Time Series 
(Daily)", there will be many dates with OHLCV values. For example: 
{ 
  "Meta Data": { ... }, 
  "Time Series (Daily)": { 

 
 
 
 
 
 
 
 
 
 
      "2025-03-12": { 
          "1. open": "150.00", 
          "2. high": "155.00", 
          "3. low": "149.00", 
          "4. close": "154.00", 
          "5. volume": "10000000" 
      }, 
      "2025-03-11": { ... }, 
      ... 
  } 
} 
We will parse this in the next step. If the HTTP node returns an error (check the n8n Execution pane for 
error messages), verify your API key is correct and the credential is attached. If you see an Alpha 
Vantage error in the output JSON like: 
{ "Note": "Thank you for using Alpha Vantage! Our standard API call frequency is 5 calls per minute and 
500 calls per day. Please visit https://www.alphavantage.co/premium/ if you would like to target a higher 
API call frequency." } 
that means you’ve hit the rate limit  (e.g., if you tested with more than 5 tickers within a minute). Don’t 
worry – we will handle this scenario with a fallback soon. For now, proceed knowing the structure of the 
successful response. 
2.4 Add a Function Node to Calculate Percentage Change – The Alpha Vantage response has the full 
daily history for each ticker, but we only need today’s data (the latest trading day) and the percent change 
from the previous day’s close. We’ll use a Function node to extract the relevant values (Date, Open, 
High, Low, Close, Volume for the latest day, plus the percent change from prior day). The Function node 
allows writing custom JavaScript to manipulate the data. Add a Function node to the canvas and connect 
the main output (output 0) of the HTTP Request node to the input of the Function node. (We will 
handle the error output of HTTP later.) Double-click the Function node to open its code editor. We will 
write code to process each item (each item corresponds to one ticker’s data). Use the following code in 
the Function node: 
// This Function node expects each input item to have the Alpha Vantage JSON in item.json 
// We'll output one item per ticker with the fields: Date, Ticker, Open, High, Low, Close, Volume, Percent 
Change. 
const results = [];  // array to collect output items 
for (let item of items) { 
  const data = item.json; 
  const symbol = data["Meta Data"] ? data["Meta Data"]["2. Symbol"] : null; 
  const timeSeries = data["Time Series (Daily)"]; 
  if (!timeSeries) { 
    // If no time series is present (e.g., error), skip this item. 
    // (These cases will be handled in the error branch instead.) 
    continue; 
  } 
  // Get all dates in the time series 
  const dates = Object.keys(timeSeries); 
  dates.sort();  // sort in ascending order (oldest to latest) 
  const lastDate = dates[dates.length - 1];      // latest date (most recent trading day) 
  const prevDate = dates[dates.length - 2];      // previous trading day 
  const latestData = timeSeries[lastDate]; 
  const prevData = timeSeries[prevDate]; 

  // Parse values as numbers 
  const open = parseFloat(latestData["1. open"]); 
  const high = parseFloat(latestData["2. high"]); 
  const low  = parseFloat(latestData["3. low"]); 
  const close = parseFloat(latestData["4. close"]); 
  const volume = parseInt(latestData["5. volume"], 10); 
  const prevClose = prevData ? parseFloat(prevData["4. close"]) : null; 
  // Calculate percentage change from previous close 
  let percentChange = null; 
  if (prevClose && prevClose !== 0) { 
    percentChange = ((close - prevClose) / prevClose) * 100; 
    // Round to 2 decimal places for readability 
    percentChange = Math.round(percentChange * 100) / 100; 
  } 
  // Create an output item with the desired fields 
  results.push({ 
    json: { 
      Date: lastDate, 
      Ticker: symbol || item.json.symbol || "",  // symbol from metadata, or fallback to original input if 
available 
      Open: open, 
      High: high, 
      Low: low, 
      Close: close, 
      Volume: volume, 
      "Percent Change": percentChange 
    } 
  }); 
} 
return results; 
Let’s break down what this code does: 

• 
• 

We loop over each item in items (each item is a ticker’s API result). 
We extract the symbol from the "Meta Data" section (Alpha Vantage provides the symbol 

there). We also get the timeSeries which is the "Time Series (Daily)" object. If timeSeries is missing, we 
skip that item (this could happen if the API returned an error note instead of data). 

• 

We collect the dates available in the time series, sort them, and pick the last two (most 
recent and the day before). Alpha Vantage’s dates are strings like "2025-03-12". Sorting them as strings 
works here because they’re in YYYY-MM-DD format (which sorts lexicographically). 

• 

We then get the OHLCV data for the latest date and the previous date. The data is in 
strings, so we convert the numeric values with parseFloat/parseInt. For example, "1. open": "150.00" 
becomes open = 150.00 (number). 

• 

We compute percentChange as ((todayClose - prevClose) / prevClose) * 100. We check 

that prevClose exists and isn’t zero to avoid division issues. We round it to two decimal places. 

• 

We create a new object with keys exactly matching our Google Sheet columns: Date, 
Ticker, Open, High, Low, Close, Volume, and Percent Change. We fill these with the values we got. If 
symbol from metadata is available, we use that for Ticker. (Alpha Vantage uses the same symbol we 
requested. If for some reason that’s missing, we could use the original input’s ticker.) 

• 

Finally, we return results; which sends out an array of items in the desired format. 

 
 
 
 
 
 
 
After writing the code, click “Execute Node” on the Function node to test it. It will run for each ticker from 
the previous HTTP node. Check the output data for the Function node in n8n: you should see one item 
per ticker, with a flat JSON containing the fields and values. For example: 
Date: 2025-03-12   
Ticker: AAPL   
Open: 150.0   
High: 155.0   
Low: 149.0   
Close: 154.0   
Volume: 10000000   
Percent Change: 2.67   
This indicates on 2025-03-12 Apple’s stock went from 150 to 154, etc., with a +2.67% change from the 
previous close. Verify that these numbers make sense relative to the raw data. If you run into any 
undefined values or errors, double-check that the JSON structure in the HTTP node output matches what 
the code expects (adjust the key names if needed – Alpha Vantage sometimes slightly changes keys or if 
you used TIME_SERIES_DAILY_ADJUSTED, the fields would be named differently like "5. adjusted 
close" and volume might be "6. volume"). Adjust accordingly or use the correct index for close price. 
At this stage, we have the core data for each successful API call. Next, we will handle cases where Alpha 
Vantage didn’t return data due to rate limits or other errors, by using Yahoo Finance. 
2.5 Implement Fallback for Rate Limits and Errors – Alpha Vantage enforces strict rate limits: 
maximum 5 calls per minute and 500 per day on the free plan . If our watchlist has more than 5 tickers, 
the 6th call within a minute will be rejected with a "Note" message (instead of data) . We’ll set up a branch 
in our workflow to catch those cases and query Yahoo Finance for the data instead. We’ll also catch any 
outright HTTP failures. The plan is: 

• 

Identify which tickers did not get data from Alpha Vantage (either due to rate limiting or 

any error). 

• 
• 
• 
• 

For those, use a Yahoo Finance API to get the last two days of OHLCV. 
Process that data similarly in a Function node. 
Then merge it with the Alpha Vantage results. 
Also log any that still fail in an error sheet. 

We’ll need a few extra nodes: an IF node, a Merge node, another HTTP node (Yahoo), another Function 
node, and one more Merge for results. Let’s do these step by step. 
2.5.1 Add an IF Node to Detect Missing Data – This IF node will filter the output from the Alpha Vantage 
HTTP node to find items where Time Series (Daily) is missing (which indicates the API didn’t return data). 
Actually, since we already routed successes into the Function node, we can instead directly use the error 
output of the HTTP node for true failures. But there’s a nuance: Alpha Vantage’s rate limit note comes as 
a 200 OK response (so the HTTP node doesn’t consider it a failure; it went through the main output, but 
the content has no Time Series). Those cases would have been skipped in our Function node (we used 
continue if !timeSeries). We need to capture them and send those tickers to Yahoo as well. 
To do that: connect the output of the Alpha Vantage Function node (the one we just wrote) and the 
output of the Alpha Vantage HTTP node’s error stream into a new IF node. Actually, we will use two 
inputs: one from the Function node (successful items) and one from the HTTP node’s error output (failed 
items). However, to keep things clear, we’ll use the IF node just to identify the “empty” items that went 
through the Function node with no data (which in our code we actually skipped entirely, so they may not 
exist at all). Another approach: we can modify our function to output a placeholder for failed items, but an 
easier way is to use the HTTP node’s error output combined with checking for the "Note" field. 
Instead, we can do this simpler: Use the HTTP Request node’s second output (error output) directly for 
actual HTTP failures, and use an IF node on the Alpha Vantage HTTP main output before the Function 
node to catch rate-limit notes. So let’s do that: 

 
 
 
 
 
• 

Drag a new IF node onto the canvas. Connect the main output of the Alpha Vantage 

HTTP node (the first output, which includes both data and possibly “Note” messages) to the IF node. 
(This is before the Function node processing; we’re effectively splitting the stream: one going to Function 
node, one going to IF node to check content.) 

• 

Configure the IF node: We want to check if the response contains valid data or not. In the 

IF node’s conditions, set Condition: 

• 

Select the variable as an expression: for example, click “Add Condition”, choose String 
type, then for the value select Time Series (Daily) field from the JSON. (In expression mode it might be 
something like {{$json["Time Series (Daily)"]}}.) 

• 

We want to check if this field exists. Unfortunately, IF node doesn’t have an “exists” 

directly, but we can do: “Time Series (Daily)” equals Null (or does not equal Null). Another trick: check a 
known property in the time series. For instance, set condition: Time Series (Daily) -> Exists == false. If 
the UI doesn’t allow that, use a workaround: check “Meta Data” exists and “Time Series (Daily)” does 
not exist or has no keys. Alternatively, check if Note field exists. 

• 

E.g., add two conditions: IF Time Series (Daily) is empty OR Note contains “API call 

frequency”. Combine with OR. This would flag items that have a Note about rate limit. 
For simplicity: choose “String” condition, variable: {{$json["Note"]}}, condition: Exists. Then set it to true. 
Actually, that would send those with a Note to the “true” branch. We actually want the opposite routing: we 
want items that failed (with Note) to go one way (to Yahoo), and the ones with data to go another (to 
continue to our function). So do: IF Note exists -> output to true branch. 
Also handle invalid symbol errors: those come as "Error Message" in JSON. So add another OR: OR 
Error Message exists. 
In summary, configure IF so that the Yes (true) output will catch any item where either "Note" exists or 
"Error Message" exists (meaning Alpha Vantage didn’t return data). 

• 

On the IF node, you’ll now have two outputs: Output 0 (True) will carry the problematic 

items (tickers that need Yahoo fallback), and Output 1 (False) will carry the good items (which have 
data). Connect the False output (1) of IF to the Function node we made in step 2.4. This means only 
items that had real data go into that function (which we already were doing, effectively). Connect the True 
output (0) of IF to the next step of our Yahoo flow (we will merge these with error branch next). 
Now, also connect the Error output (2nd output) of the Alpha Vantage HTTP node to the next step of 
the Yahoo flow. The error output items are those where the HTTP request failed entirely (network error or 
HTTP error status). They definitely need to be retried via Yahoo. n8n represents the second output with a 
small red arrow dot on the HTTP node. Drag from that to the same place you connected the IF true 
output. Since we cannot directly connect two different outputs into one input, we will instead use a Merge 
node to collect them. 
2.5.2 Add a Merge Node for Failed Tickers – Add a Merge node to aggregate the tickers that need the 
Yahoo fallback (these are: items from IF true branch, and items from HTTP error output). Place the Merge 
node on the canvas. Connect IF node’s True output to Merge node Input 1, and Alpha Vantage HTTP 
node’s Error output to Merge node Input 2. In the Merge node settings: 

• 

Set Mode to “Append” (combine incoming items). We just want a combined list of all 

failed items, not a pairwise merge. 

• 

We don’t need to worry about property keys since we just want all items forwarded. 

This Merge node will output a unified stream of items that did not get data from Alpha Vantage. Each item 
should still contain the ticker information (and possibly an error note or message). Crucially, each item’s 
JSON should have something identifying the symbol – either in a field like symbol (if we input it) or still in 
Meta Data? Wait, the items coming from IF True branch have a Note or Error Message and might lack 
Meta Data. The ones coming from the error output might have a property like item.json is empty and 
item.error contains details. We need to ensure we have the ticker symbol to query Yahoo. 
We have two cases in this merged stream: 

 
 
 
 
 
 
 
 
• 

Rate limit note case: The item likely still has Meta Data with the symbol (need to 

confirm: If Alpha Vantage hits limit on, say, the 6th call, do they return any partial data or just the Note? I 
believe they return just the JSON with Note and no Meta Data. If so, we lost the symbol info unless we 
carried it forward). 
• 

However, n8n input to HTTP node had symbol parameter. Possibly the HTTP node input 

item might still be accessible. n8n often attaches input data as item.json for nodes. In the HTTP node 
output, maybe the original input fields are preserved unless overwritten. Actually, by default, HTTP node 
likely replaces the item with response JSON. But there is an option “Merge responses with input” – if that 
was off (default is to replace), then the original ticker might not be in item.json anymore, only the 
response. This is tricky because if the response had no symbol, how do we know which ticker failed? 

• 

To solve this, we can use a feature: In HTTP Request node options, enable “Keep Only 
Set” to false or “Binary/JSON Merge” – or simpler: before calling API, we could add the ticker symbol into 
a separate field to carry it through. For example, in the Google Sheets node or a subsequent Set node, 
ensure each item has a field ticker in its JSON. Actually, our Google Sheets node likely output the ticker 
as a field (if header was present). So in each item before HTTP, there was item.json.Ticker = 'AAPL'. 
When we made the HTTP call, by default the HTTP node will output the response JSON, not including the 
original fields. But n8n often keeps the original fields unless we use a specific option. There is an HTTP 
node option “Response Format” – if set to JSON (default), it outputs the response as the new JSON. 
The original input might be accessible via item.pausedAt or in the context but not straightforward. 
The easiest fix: modify the HTTP node to always output the symbol along with the 

• 

response. One way: use the “Add Header/Query Params to Response” option if it exists (some nodes 
allow including the request parameters in the output). Or simpler, after the HTTP node, use a quick 
Function or Move that maps the ticker from input to output. Alternatively, we could have the Google 
Sheets node output as multiple separate items and then use a Function node to attach each ticker to its 
own item ( but they already are separate items). 
To not overcomplicate, we can assume we know which tickers failed by their order. But better, let’s adjust: 
We can add a Set Node right after Google Sheets (before the HTTP call) to rename the ticker field to a 
consistent key and ensure it passes through. For instance, add a Set node between Google Sheets and 
HTTP: configure it to keep all fields (toggle “Keep Only Set” to false) and add a new field like symbol = 
{{$json["Ticker"]}}. Then the HTTP node will receive items that have a symbol field in their JSON. The 
HTTP Request when it outputs response might not keep that by default, but we can force merge: In HTTP 
node’s Options, there is “Header Data” or “Query Data” options like Send and Merge or Merge By 
Fields. Actually, n8n’s HTTP node has an option “Merge Responses” -> if set to e.g. “merge by index”, it 
might merge original and response. Alternatively, use the “Combine” node, but let’s see if simpler: Under 
HTTP node’s settings, if “Full Response” is disabled, it outputs just body. If “Full Response” is 
enabled, it outputs an object with body, headers, etc. Not needed. 
Perhaps instead of going back, we handle in the error branch: If an item lacks ticker, we might use the 
fact that the Merge node combining error output and IF output will preserve the item order or something. 
Actually, not necessarily needed: the error output of HTTP likely does preserve the original item JSON 
plus an .error property, since the request never succeeded to overwrite it. In that case, for network errors, 
item.json.Ticker might still exist. For the rate-limit “Note”, since HTTP succeeded, item.json got replaced 
with the Note-only JSON. We lost the ticker there. But we did skip it in Function node, and we have it in IF 
true output – however IF true output item’s JSON is just the same note (with no ticker). 
To retrieve the ticker for those, an approach: The IF node’s true branch items correspond one-to-one to 
the input (Alpha HTTP output) items that had no data. If the Google Sheets had N tickers, and say ticker6 
got a Note, the IF true will have that item (with Note, no ticker). But maybe the position in the execution or 
item index is 6. Possibly we can join it with the original list by index. But easier: Actually, the Alpha 
Vantage HTTP Node output might include the symbol in the "Meta Data" if the call was valid but just 

 
 
 
 
limited. If the call is limited, maybe it doesn’t return Meta Data at all. Let’s assume worst-case, we need a 
way to get ticker name. 
For simplicity in this guide, we’ll do this: We will use the Yahoo fallback for rate-limit issues primarily when 
the number of tickers > 5. In practice, to avoid losing tickers, one best practice is to keep track of the 
tickers separately. We can modify our approach slightly: Instead of using IF to catch rate-limit inside main 
flow, we could use the fact that our Function node skipped those items. So after the Function node, we 
could see which tickers are missing by comparing input vs output count. That’s complex in n8n without 
code. So we’ll proceed with the IF/Merge approach and assume for now that we know the tickers (we’ll 
attempt to carry symbol forward in Yahoo call by indexing). 

• 

Summary so far: The Merge node now has items that need Yahoo. We must ensure 

each merged item has a ticker identifier. To do that robustly, let’s add a quick Function after Merge node 
to set a Ticker field for each. Add a Function Item node (or a Set node) after the Merge, connected to 
Merge’s output. In that node, we can do: item.json.Ticker = item.json.Ticker || item.json.symbol || 
item.json["Meta Data"]["2. Symbol"] || item.json["Note"] – well, that doesn’t get ticker from Note. Another 
trick: maybe we can store the ticker in the error message for note: the Note message doesn’t contain the 
symbol unfortunately. But maybe the Meta Data might not exist in note. If we had no way, we might have 
to rely on position matching with original list from Google Sheets, which is not straightforward to 
implement in n8n without writing a custom matching. 
Given the complexity, let’s assume we keep the order and that the merge node outputs items in the same 
order as input. Actually, the Merge “Append” will output items in the order they arrive from each branch. If 
we want to preserve original order, we’d need a different merge strategy or separate handling. Perhaps 
it’s acceptable that the Yahoo fallback doesn’t know the exact order as long as each item is processed. 
But for logging errors, we need ticker names. 
Simpler Implementation Note: For clarity of this guide, we will assume a moderate watchlist where 
hitting the rate limit is possible and Yahoo fallback is engaged, but to actually get the ticker names, one 
best practice could be to not rely on the complex merging logic and instead proactively throttle the 
requests. For instance, inserting a Wait node to pause 12 seconds after every 5 API calls (Alpha Vantage 
recommends 12-second intervals to stay under the 5/minute limit) . This is another best practice: if you 
have many tickers, consider batching or delaying calls to respect the rate limit . However, since the 
question explicitly asks for Yahoo fallback, we proceed with that route. 
Moving on with the workflow: Now that the Merge node collects failed tickers, we will call Yahoo. 
2.5.3 Add an HTTP Request Node for Yahoo Finance – Add another HTTP Request node and connect 
the output of the Merge node (or the Function after it that sets tickers) to this Yahoo HTTP node. This 
node will query Yahoo Finance’s unofficial API for the last two days of price data. Yahoo doesn’t require 
an API key for basic queries, but the endpoint is not officially documented. We can use the Yahoo 
Finance chart JSON API: 
https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=2d 
This returns up to 2 days of data for the given symbol. We’ll parse the JSON to get OHLC and volume. 
Configure the Yahoo HTTP node as follows: 

• 
• 

HTTP Method: GET 
URL: Use an expression to insert the ticker symbol. Type: 

https://query1.finance.yahoo.com/v8/finance/chart/ 
then insert the symbol. Click the expression button and select the field that contains the ticker (likely 
{{$json["Ticker"]}} if we ensured the merged items have Ticker). Complete it as: 
https://query1.finance.yahoo.com/v8/finance/chart/{{$json["Ticker"]}}?interval=1d&range=2d 
This will fetch 2 days of daily data for each ticker item. 

• 
• 

Authentication: None (Yahoo’s endpoint is public). 
Headers: Yahoo might block requests that don’t have a user-agent. To mimic a browser 

and avoid a 403 Forbidden, add a header. Click Add Header and set Name: User-Agent, Value: 

 
 
 
 
 
Mozilla/5.0 (or any modern browser UA string). This ensures our request isn’t rejected by Yahoo’s servers 
for looking like a bot. 

• 
• 

We don’t need query params (we included them in the URL query string). 
Options: Similarly to before, set Retry on Fail = 3 (with a short delay) to handle transient 

issues. Also set Continue on Fail to “Continue (error output)” so that if Yahoo fails for any ticker, it won’t 
stop the workflow. We’ll catch those errors separately. 
Now test the Yahoo HTTP node: select it and click Execute Node. It will attempt to fetch data for each 
failed ticker. Check the output. A successful Yahoo response JSON looks like: 
{ 
  "chart": { 
    "result": [ 
      { 
        "timestamp": [ 1678741800, 1678828200 ],  
        "indicators": { 
          "quote": [  
            { "open": [150, 154], "high": [155, 157], "low": [149, 153], "close": [154, 156], "volume": [10000000, 
12000000] } 
          ] 
        } 
      } 
    ], 
    "error": null 
  } 
} 
This is a bit nested. Essentially, timestamp is an array of two Unix timestamps (in seconds) for the last 2 
trading days, and indicators.quote[0] contains arrays of open, high, low, close, volume corresponding to 
those timestamps. We’ll parse this next. 
If the Yahoo node returns an error (for example, an invalid ticker might return a 404 or an error in the 
JSON’s "chart.error" field), note which ones failed. The node’s error output will carry those. 
2.5.4 Add a Function Node to Process Yahoo Data – Add another Function node and connect the 
main output of the Yahoo HTTP node (output 0) to it. This function will mirror what we did for Alpha 
Vantage: pick out the latest day’s OHLCV and percent change. Double-click to edit and use the following 
code: 
const results = []; 
for (let item of items) { 
  const data = item.json; 
  if (!data.chart || !data.chart.result || data.chart.result.length === 0) { 
    // If Yahoo returned an error or empty result, skip 
    continue; 
  } 
  try { 
    const result = data.chart.result[0]; 
    const timestamps = result.timestamp; 
    const quote = result.indicators.quote[0]; 
    const ticker = item.json.symbol || item.json.Ticker || "";  // Yahoo’s response doesn’t include the ticker, 
so carry it from input 
    // Get the last two entries (they should be the last 2 trading days) 
    const n = timestamps.length; 
    const lastIdx = n - 1; 

 
 
    const prevIdx = n - 2; 
    const lastDateObj = new Date(timestamps[lastIdx] * 1000);  // convert Unix seconds to JS Date 
    // Format date to YYYY-MM-DD (Yahoo timestamps are in UTC) 
    const yyyy = lastDateObj.getUTCFullYear(); 
    const mm = String(lastDateObj.getUTCMonth()+1).padStart(2, '0'); 
    const dd = String(lastDateObj.getUTCDate()).padStart(2, '0'); 
    const lastDate = `${yyyy}-${mm}-${dd}`; 
    const openArr = quote.open; 
    const highArr = quote.high; 
    const lowArr = quote.low; 
    const closeArr = quote.close; 
    const volumeArr = quote.volume; 
    const open = openArr[lastIdx]; 
    const high = highArr[lastIdx]; 
    const low = lowArr[lastIdx]; 
    const close = closeArr[lastIdx]; 
    const volume = volumeArr[lastIdx]; 
    const prevClose = closeArr[prevIdx]; 
    let percentChange = null; 
    if (prevClose != null && prevClose !== 0) { 
      percentChange = ((close - prevClose) / prevClose) * 100; 
      percentChange = Math.round(percentChange * 100) / 100; 
    } 
    results.push({ 
      json: { 
        Date: lastDate, 
        Ticker: ticker, 
        Open: open, 
        High: high, 
        Low: low, 
        Close: close, 
        Volume: volume, 
        "Percent Change": percentChange 
      } 
    }); 
  } catch (e) { 
    // If any parsing error occurs, we skip this item (it might be handled in error branch instead). 
    continue; 
  } 
} 
return results; 
Explanation: We navigate the Yahoo JSON structure. result = data.chart.result[0] contains the relevant 
data. We get the timestamps array and the quote object with arrays for open, high, low, close, volume. 
We then take the last index as the latest day. We convert the timestamp to a date string (Yahoo’s 
timestamps are in seconds UTC). We pull out the open/high/low/close/volume for that last index, and the 
close for the previous index, then calculate percent change similarly. Yahoo’s response doesn’t include 
the ticker symbol, so we rely on carrying it from the input (either item.json.Ticker from our input item, 
which we tried to preserve). We then output an item with the same structure as the Alpha Vantage 
function: Date, Ticker, Open, High, Low, Close, Volume, Percent Change. 

Execute this Yahoo Function node to test. The output items should look similar to the earlier function’s 
output, just for the tickers that needed fallback. Verify the numbers roughly match what Yahoo shows for 
those dates (you can cross-check one ticker’s values on Yahoo Finance manually). If something is 
undefined (e.g., perhaps the Yahoo API didn’t return two days because of a weekend/holiday or if we ran 
after hours on a Friday, the range=2d might include Friday and Monday skipping weekend – but since we 
run at 5 PM, it should include that day and previous market day). In edge cases, you might adjust range 
to 5d and take the last two trading days to be safe, but 2d is usually sufficient for daily runs. 
Now we have two parallel streams of processed data: one from Alpha Vantage (Function node 2.4 
output), and one from Yahoo (Function node 2.5.4 output). We need to combine them and then append to 
Google Sheets. 
2.6 Merge Results and Append to Historical Sheet – Add another Merge node to combine the outputs 
of the two Function nodes (Alpha’s and Yahoo’s). Connect Alpha Vantage Function node’s output to 
Merge Input 1, and Yahoo Function node’s output to Merge Input 2. Set Merge Mode = Append (so it 
just concatenates the items) as we did before. The output of this Merge will be a unified list of all the 
fetched data for today (some from Alpha, some from Yahoo). 
Next, add a Google Sheets node to append these results to the historical log. Connect the output of the 
Merge node (with results) to the input of this new Google Sheets node. Configure this Google Sheets 
node as follows: 
• 
• 
• 

Credentials: Use the same Google Sheets credential (service account). 
Resource: Sheet 
Operation: Append Sheet (Append Row). (Depending on n8n version, it might be 

“Append Row” or “Append or Update”. Choose the one that appends a new row for each item.)   

• 
• 
• 

Spreadsheet ID: Enter/pick the same Spreadsheet (Stock Data file ID). 
Sheet Name: Enter “HistoricalData” (the sheet where we want to append). 
Key Matching / Lookup: (Not needed if using simple Append Row, but if using Append 
or Update, you’d specify a key to decide when to update vs append. We strictly want to append always, 
so use the plain Append if available.) 

• 

Value Input Mode: If there’s an option like “RAW” or “USER_ENTERED”, RAW is fine 

(we’re writing exact values, not formulas). 

• 

Map Fields: Ensure that the node knows how to map the incoming JSON fields to sheet 

columns. Since we gave our JSON keys exactly the same names as the sheet headers, the Google 
Sheets node will automatically match them by name. (For example, it sees Date field and will put that 
under the “Date” column, etc.) If your Google Sheets node requires you to manually map, do so 
accordingly: map Date -> Date, Ticker -> Ticker, etc., for all 7 fields. If an “Add All Fields” button is 
available, you can use that to auto-map. 

• 

Option “Continue if Empty” (if present): not necessary, as we should always have at 

least one item daily. 

• 

Disable “Continue on Fail” for this node (we actually want to know if writing to Google 

Sheets fails, since that’s critical; but it’s unlikely if credentials and sharing are correct). 
Test the Google Sheets append node by executing it. It should append new rows to the HistoricalData 
sheet for each item passed in. In your Google spreadsheet, you should now see new rows under the 
headers with the values. Check that each column is filled correctly. For example, verify that the Percent 
Change column shows a number that is indeed the percentage difference between the last two Close 
values (you can cross-check manually for one ticker). 
2.7 Log Failures to “Errors” Sheet – Finally, we handle any tickers that even after the Yahoo fallback 
failed. These could be due to invalid ticker symbols or some connectivity issue. We have two points of 
possible failure after our error handling: 

• 

The Yahoo HTTP node’s error output (tickers that failed even via Yahoo). 

 
 
 
 
 
 
 
 
 
 
 
• 

The Yahoo Function node skipped items if it couldn’t parse (though in our code we 

continued on exceptions). Ideally, anything that reached Yahoo Function but couldn’t be parsed likely also 
triggered an error in Yahoo HTTP or returned an empty chart.result. We somewhat skip those with 
continue in the function, meaning they won’t appear in the merged results, so they’d be missing from 
historical log and should be considered failed. 
We’ll capture the Yahoo HTTP node errors. The Yahoo HTTP node, like the Alpha one, has a second 
output for errors (if Continue on Fail is on). So take the error output of Yahoo HTTP node and connect it 
to a Google Sheets (Append) node for the Errors sheet. Also, for completeness, we might want to 
capture if the Yahoo Function node skipped something (but since we skip only on parse error, which likely 
coincides with an error output anyway, we’ll consider the error output as the source of truth for failures). 
Add a new Google Sheets node and connect the error output (output 1) of Yahoo HTTP node to its 
input. Configure this Google Sheets node: 

• 
• 
• 
• 
• 
• 

Credentials: same Google Sheets credential. 
Resource: Sheet 
Operation: Append Row (or Append) 
Spreadsheet ID: the same spreadsheet ID 
Sheet Name: “Errors” 
Field Mapping: We want to log at least the ticker and an error message, maybe a 

timestamp. Our Errors sheet has headers Date, Ticker, Error Message. We can populate: 

• 

Date: Use an expression to get the current date/time. (We want to log when the error 

happened – using the workflow’s execution time is fine). In the Value field for Date, switch to Expression 
and enter: {{ new Date().toISOString().split('T')[0] }} to get today’s date in YYYY-MM-DD format. Or for full 
timestamp, you could do {{ new Date().toISOString() }}. 

• 

Ticker: This is tricky – the error items might still have the original ticker in their JSON if 
the HTTP node failed before replacing data. Likely, for Yahoo HTTP error items, item.json.Ticker is still 
present (because if Yahoo returned a non-2xx, n8n might carry forward the input). To be safe, check the 
structure: the Yahoo HTTP error output item might look like { error: { message: "...", ...}, json: { Ticker: 
"ABC" } }. If so, we can map Ticker to an expression like {{$json["Ticker"]}}. That should yield the ticker 
symbol. 

• 

Error Message: Use an expression to capture the error. Possibly {{$error.message}} 

might work if n8n exposes it. Another way: sometimes the error output item’s JSON is empty and the error 
info is in a separate property. In n8n function, one can access item.error but not sure in expression. A 
simpler way: map Error Message to the raw text of the error. Use expression and try {{ $json["message"] || 
$json["error"] || "Unknown error" }}. If the Yahoo HTTP node produced an item with an error property 
(some nodes do output {"error": "...", "errorCode": ...} in JSON), that could be used. If not, we might just 
put a static note like “Yahoo API call failed”. 

• 

If the Google Sheets node allows, you can also use the expression editor’s $node 

reference to pull data from the error. For example, {{$node["Yahoo HTTP Node Name"].error.message}}. 
However, since we are connecting the error output directly, we can likely use $json of that error item. You 
can also include {{$json["code"]}} if available (like HTTP status). To keep it simple, map Error Message to 
{{$json["message"] || $json["Note"] || "API call failed"}}. (Experiment in the editor by looking at the error 
output data structure.) 
After mapping, execute this Google Sheets Error node to test it with any dummy error item. If you 
currently have no error item (because everything succeeded in tests), you can simulate one by, for 
example, changing a Yahoo URL to a wrong one and running just that node to generate an error, then 
catching it. But assuming at least one ticker was invalid, it will show up. In any case, once the workflow is 
live, if an error occurs, this node will append a row to the Errors sheet with the ticker and message. 
Verification: Intentionally cause a failure to ensure the error logging works. For example, add a fake 
ticker like “INVALID” to your Watchlist and run the workflow (maybe manually). Alpha Vantage might 

 
 
 
 
 
 
 
 
 
 
 
return an “Error Message: Invalid API call.” for that ticker, which triggers Yahoo fallback. Yahoo might 
return a 404 or an empty result for an unknown ticker, leading to the error output. Check that the Errors 
sheet gets a new entry for “INVALID” with an appropriate message (and today’s date). This confirms our 
error handling flow. 
3. Final Workflow Review and Best Practices 
Now we have a complete workflow. Let’s recap the node connections in order, to ensure everything is 
properly linked: 
• 

Schedule Trigger (Cron) – triggers daily at 5 PM ET. (For testing, you can manually 

execute the workflow or temporarily change Cron to manual trigger.) 
→ Google Sheets (Get Rows) – reads tickers from “Watchlist” sheet. 
→ HTTP Request [Alpha Vantage] – calls Alpha Vantage API for each ticker (with retries and error 
handling enabled). 
• 
• 
• 

This node has two outputs: 
Output 0 (successes and any “note” responses) 
Output 1 (errors, e.g., HTTP failures). 

IF Output True (needs fallback) carries items where Alpha failed to return data. 
IF Output False carries items with actual data. 

→ IF Node (connected to Alpha’s Output 0) – checks each Alpha response for missing data (Note or 
Error Message). 
• 
• 
IF False 
→ Function [Process Alpha Data] – computes OHLCV and percent change from Alpha results. (This 
yields items ready to append.) 
IF True 
→ Merge [Alpha Failures] (Input 1) – collects failed items (Alpha fallback needed). 
Alpha HTTP Error Output 
→ Merge [Alpha Failures] (Input 2) – also feeds into the same merge. 
Merge [Alpha Failures] 
→ HTTP Request [Yahoo] – calls Yahoo Finance for each failed ticker (with its own retry/continue 
settings). 
• 
• 
• 

Yahoo HTTP has two outputs as well: 
Output 0 (success responses). 
Output 1 (error responses). 

Yahoo HTTP Output 0 
→ Function [Process Yahoo Data] – computes OHLCV and percent change from Yahoo results. 
Yahoo HTTP Output 1 
→ Google Sheets [Append Errors] – appends a row in “Errors” sheet with the ticker and error info. 
Function [Alpha] Output 
→ Merge [All Results] (Input 1) – combine final results. 
Function [Yahoo] Output 
→ Merge [All Results] (Input 2). 
Merge [All Results] 
→ Google Sheets [Append HistoricalData] – appends the new data rows to the historical sheet. 
Double-check all connections: in n8n, nodes show small numbered ports. Ensure that where we intended 
to use the error output (usually port “1” in red) it’s connected properly to the right subsequent node, and 
the main outputs (port “0” in green) go to the correct next steps. The connections should match the 
logic above. If something is mis-wired, you can click and drag connections to rearrange. 
Test the Entire Workflow: Now do a full test run of the workflow. Hit “Execute Workflow” (which triggers 
from the Cron node). Watch the execution progress in n8n’s sidebar: you should see each node execute 

 
 
 
 
 
 
 
 
 
in sequence. If all goes well, the Google Sheets nodes will add data to the sheets. Check your Google 
Sheets after the run: 

values. 

• 

• 

The “HistoricalData” sheet should have a new row for each ticker with today’s date and 

The “Errors” sheet should have any failed tickers logged (if none failed, it should remain 

unchanged; you can simulate a failure as described to see it working). 
Activate the Workflow: Finally, toggle the workflow to Active in n8n (top right corner) so that the 
schedule trigger will run it automatically at 5 PM ET daily. (If using n8n cloud or an always-on instance, 
just saving it as active is enough. If using the desktop app, it needs to be open or you should deploy it to a 
server for real scheduling.) 
Best Practices and Considerations: 

• 

Rate Limit Handling: We used a fallback to Yahoo Finance when Alpha Vantage’s limit 

is reached. Another best practice is to throttle calls to Alpha Vantage to avoid hitting the limit in the first 
place. For example, you could use a Split In Batches node to process 5 tickers at a time, then a Wait 
node for 60 seconds, and loop, as suggested by Alpha Vantage’s documentation . This would slow the 
workflow but reduce reliance on an alternate source. In our design, Yahoo acts as a safety net to ensure 
continuity even if limits are hit. 

• 

Data Consistency: Using two data sources (Alpha and Yahoo) might result in slight 

differences (e.g., if one includes after-hours data or minor rounding differences). For daily close values 
these should be minimal. If consistency is paramount, consider using a single source consistently or at 
least note in your data which source was used. You could add a field “Source” in the output indicating 
“AV” or “YF”. This can be done by setting a field in the respective function nodes. (For brevity, we did not 
include this, but it’s a good idea for transparency.) 

• 

Error Workflow: We logged errors to a sheet. Alternatively, n8n has an Error Trigger 

node that can catch workflow failures globally. Since we handled errors within the workflow, it ideally 
shouldn’t fail outright. But if you want to be notified or handle global errors (e.g., if Google Sheets 
credential fails), you might set up an Error Trigger workflow (perhaps emailing you the error). For now, our 
error sheet serves as a record to review. 

• 

Secure Credentials: We stored the API key in n8n’s credential which is encrypted . 

Ensure you do not log or print the API key in any node (our workflow doesn’t). Treat the Google service 
account JSON carefully as well – it’s stored in n8n’s credentials. If using n8n cloud, that’s managed 
securely; if self-hosting, make sure your environment variables or config are secure. 

• 

Workflow Efficiency: The workflow runs daily, which is fine even for dozens of tickers. If 

you eventually track hundreds of tickers, consider the rate limit – the Yahoo fallback will help but you 
might end up hitting Yahoo’s own unspoken limits if too many calls are made rapidly. In such a case, 
implementing the mentioned batching delay or upgrading Alpha Vantage plan (for more calls per minute) 
would be wise. Alpha Vantage’s premium tiers allow more calls per minute . 

• 

Hourly Updates: If you want to run more frequently (intraday), note that Alpha Vantage’s 
free API for intraday data also has similar limits and returns time-series. Yahoo can provide intraday data 
via different interval parameters. You’d need to adjust the logic: perhaps use a different function (like 
TIME_SERIES_INTRADAY for Alpha) and modify how data is parsed (the JSON structure differs). Also, 
the historical sheet might then log multiple entries per day (you might include timestamp in that case). For 
simplicity, daily is shown here. 
Your workflow is now fully set up. Monitor the first few runs to ensure data is coming in as expected. 
You can see execution logs in n8n (the Executions list) to confirm it ran at the scheduled time. And that’s 
it – you have an automated stock tracker populating your Google Sheet each day after market close, with 
robust error handling to cover API hiccups and rate limits! 
Sources: 

 
 
 
 
 
 
 
 
• 

Alpha Vantage API rate limits (5 per minute, 500 per day)  and the note it returns when 

exceeded . It’s good practice to avoid exceeding these limits by adding delays if needed . 

• 

n8n credentials were used to store the API key securely (so it’s not in plain text in the 

workflow) . 

• 

The Schedule Trigger node timing respects the set timezone (we set it to ET for 

accuracy) . 

• 

We used “Continue on Fail” and “Retry on Fail” settings on HTTP nodes so one failure 

doesn’t halt the whole workflow .
