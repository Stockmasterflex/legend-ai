# Phase 3_ Technical Analysis Workflow

> Imported from: `/Users/kyleholthaus/Downloads/repoLAI Docs /Phase 3_ Technical Analysis Workflow.pdf`
> Converted: 2025-09-11 21:33:38

Phase 3: Technical Analysis Workflow 

Introduction 
n8n is a no-code/low-code workflow automation tool that can connect to various services (like Google 
Sheets) and run custom logic (via code nodes). In this guide, we will build a professional-grade stock 
technical analysis workflow step by step. The workflow will read historical stock price data (OHLCV: 
Open, High, Low, Close, Volume) from Google Sheets, compute multiple technical indicators, generate 
trading signals by combining those indicators, and write the results back to Google Sheets. We’ll also 
ensure the system supports backtesting on historical data and handles errors (like API rate limits or 
missing data) gracefully. Each step includes background theory (with daily vs. weekly insights), common 
pitfalls to avoid, exact n8n node configurations, and full JavaScript code for Function nodes so even a 
beginner can follow along. 
Before you start, make sure you have: 

• 
• 

Access to an n8n instance (self-hosted or cloud) where you can create workflows. 
A Google Sheets API credential set up in n8n (OAuth credentials) to allow reading and 

writing your spreadsheet. 

• 

A Google Sheets document prepared with stock data (or the ability to input it). The data 
should include at least Date, Open, High, Low, Close, Volume for each stock ticker you want to analyze. 
Ideally, use one sheet per ticker for simplicity (you can use multiple tickers in one sheet too, but separate 
sheets simplifies the upsert logic). 

• 

Basic familiarity with adding nodes in n8n. (No prior coding experience is needed – we 

provide all the code and explain where to put it.) 
Throughout this guide, we’ll use clear sections and lists. Follow the steps in order – by the end, you’ll 
have a workflow that retrieves data, computes indicators like SMA/EMA (20, 50, 200), RSI, MACD, 
Bollinger Bands, Volume trends, Support/Resistance, Stochastic, ATR, then produces a combined 
buy/sell signal with a strength score, writes it to Google Sheets, and can run on historical data for 
backtesting. Let’s dive in! 
Workflow Overview 
To give a roadmap, here’s what the final workflow will do: 

1. 

Retrieve OHLCV Data from Google Sheets: An n8n Google Sheets node will fetch 

historical price data for one or multiple stock tickers. If multiple tickers are needed, the workflow will loop 
through them efficiently without exceeding Google’s API rate limits. 

2. 

Calculate Technical Indicators: Using n8n Function nodes (which run JavaScript), the 

workflow will compute a suite of technical indicators for the price data: 

• 

Moving Averages (Simple and Exponential for 20-day, 50-day, 200-day) – to gauge 

trends and key support/resistance levels. 

• 

Relative Strength Index (RSI, 14-period) – to measure momentum and identify 

overbought/oversold conditions. 

• 

Moving Average Convergence Divergence (MACD, 12-26-9) – to assess trend 

momentum and crossover signals. 

• 

Bollinger Bands (20-period SMA ±2 std dev) and Band Width – to evaluate volatility and 

potential breakouts or mean-reversion setups. 

• 

Volume Analysis – e.g. volume moving average and volume spike detection – to confirm 
price moves (since rising prices on rising volume signal strength, whereas breakouts on low volume may 
be false). 
• 

Support and Resistance levels – to identify recent price floors and ceilings from the data 

(helpful for contextualizing the signals in a larger trend ). 

 
 
 
 
 
 
 
 
 
 
 
 
 
• 

Advanced oscillators: Stochastic Oscillator (14,3) – another momentum indicator for 

overbought/oversold signals, and Average True Range (ATR, 14) – a volatility gauge for understanding 
price range swings. 
3. 

Generate Trading Signals: A final Function node will combine the indicators into a 

cohesive strategy. This will implement logic that professional traders use: for example, require multiple 
indicators to align for a Buy or Sell signal to reduce false alarms. It will also incorporate volume-based 
confirmation (e.g., only trust breakouts if volume is above average) and produce a signal strength 
score (e.g., how many of the indicators are in agreement) which can be tuned for sensitivity. 

4. 

Write Results to Google Sheets: The workflow will output the computed indicator 

values and the final signal for each ticker back into Google Sheets. Each row (by date) will be updated 
with new columns for SMA20, EMA20, RSI, Signal, etc., or a new row will be appended if it’s a new date. 
We’ll use Google Sheet’s “Append or Update” (upsert) capability so that running the workflow daily will 
just update that day’s data without duplicating rows . 

5. 

Support Historical Backtesting: Because the workflow computes indicators for all 

historical data provided, you can use it to backtest – i.e. evaluate how your strategy would have 
performed in the past. By feeding in past data and storing the output signals, you can later analyze, for 
example, how often a “Buy” signal led to a price increase. We’ll discuss how to use the output for 
backtesting analysis. 

6. 

Error Handling: We’ll set up the workflow to handle common issues gracefully. This 

includes managing missing or incomplete data (e.g., skipping calculation if not enough data points for a 
200-day SMA), handling any ticker that fails (so one bad ticker doesn’t stop the whole workflow), and 
crucially, respecting Google’s API rate limits by throttling requests (using n8n’s Wait node or the “Retry on 
Fail” setting). 
Each step below will guide you on how to implement these in n8n, with practical tips and fully working 
code. 
Step 1: Retrieving OHLCV Data from Google Sheets 
To start, we need to get historical stock data into n8n. We assume you have a Google Sheet containing 
your stock price data. You might have one sheet per ticker (e.g., “AAPL” sheet for Apple with its OHLCV 
data, “MSFT” sheet for Microsoft, etc.), or a single sheet with a column identifying the ticker. This guide 
will use one sheet per ticker for clarity. 
1.1 Prepare the Google Sheet(s): 
Make sure your Google Sheet has columns for Date, Open, High, Low, Close, Volume for each stock. The 
Date should be in a consistent format. If using multiple sheets, name each sheet by the ticker symbol (or 
some identifier). Ensure your Google Sheets API credentials are set up in n8n (in Credentials section) so 
n8n can access the data. 
1.2 Add a Google Sheets Read Node: 
In your n8n editor, add the Google Sheets node. Configure it as follows (using the node’s UI settings): 
Credential: Select your Google Sheets credential (this authorizes n8n to access your 

• 

Google Drive/Sheets). 

• 

Resource: Choose Spreadsheet (File) if you have multiple sheets to manage, or Sheet 

if directly referencing a single sheet. Here we’ll use Sheet (within a document). 

• 

Operation: Select “Get Many Rows” (or in newer n8n versions, this might simply be 

Read or Lookup Rows – essentially we want to retrieve all rows of data). This will fetch all existing rows 
from the sheet. 
• 

Document: Select your Google Sheet file. (You can choose By URL or From List. Using 

the file’s URL or the file picker is fine.) 

• 

Sheet: If you use one ticker per sheet, you’ll eventually make this dynamic. For now, pick 

one sheet (e.g., the first ticker you want to test with, say “AAPL”). We will expand to multiple tickers in a 
loop later. 

 
 
 
 
 
 
 
 
 
 
• 

Range or Table: You can usually leave these blank to fetch the entire sheet, or specify 

the range (e.g., A:F to cover columns A through F if those contain Date…Volume). If your sheet has 
headers in the first row (recommended), keep “Use Header Row” enabled so the node returns objects 
with keys like “Date”, “Open”, etc. 
Now execute this node once (by clicking Execute Node). If configured correctly, it should output an array 
of items, each with JSON data like: { "Date": "2025-01-01", "Open": "135.5", "High": "140.0", "Low": 
"134.8", "Close": "139.2", "Volume": "100320000" } (numbers likely as strings). We’ll parse and use these 
in later nodes. 
1.3 Handling Multiple Tickers Efficiently: 
If you have multiple stock tickers to analyze, you have two main approaches: 

• 

Option A: One workflow run per ticker – You could parameterize the workflow with a 

ticker name and run it separately for each (less efficient if many tickers, but simpler logic). 

• 

Option B: Loop inside one workflow – Use n8n to loop through a list of tickers and 

process each sequentially. This is efficient and ensures you don’t hammer the API with concurrent 
requests. We’ll describe the loop approach using n8n’s built-in nodes. 
For Option B, you need a list of tickers. You can maintain this list in the workflow (e.g., in a Set node or 
read from a “tickers” sheet). For simplicity, let’s assume you know the tickers (like 
["AAPL","MSFT","GOOG"]). You can use an Execute Workflow node, feed it one ticker at a time, or use 
a Split In Batches / Loop combination: 

• 

Add an Inject (or Trigger node of your choice to start the workflow) – for manual runs, 

you can use Start node. 

• 

Add a Set node (optional) to define the list of tickers. In the Set node, add a field 

“tickerList” with a value like ["AAPL","MSFT"]. Toggle Keep Only Set if you want this node to output just 
that. This will output one item with an array of tickers. 

Now add a Split In Batches node (or Loop node). Connect the Set node to it. Configure 

• 
Split In Batches: 
• 
• 

Batch Size: 1 (to handle one ticker at a time). 
This node will take the array from the Set and iterate through it. Connect its output to your 

Google Sheets Read node. 

• 

In the Google Sheets Read node, we need to make the sheet selection dynamic based 

on the current ticker. Since we output tickers one by one from the batch, the ticker value will be accessible 
as an expression. For example, in the Sheet field, choose “By Name” and enter an expression like 
{{$json["tickerList"]}} (if the Set node output the ticker in a field named tickerList). Alternatively, adjust the 
Set node to output items each with a field “ticker” (and use multiple output items). Another simple way: 
use a Function node to output one item per ticker from the array (loop through tickerList and return 
tickers.map(t => ({ json: {ticker: t} }));). Then connect that to Google Sheets node and use 
{{$json["ticker"]}} as the sheet name expression. The key is that the Google Sheets node’s Sheet field 
should dynamically pick the sheet by ticker name. 

• 

Enable Wait Between Batches if using SplitInBatches (in newer n8n, a Wait node can be 

inserted inside the loop structure). We will address the wait in the next part about rate limits. 

• 

After the Google Sheets node (inside the loop), connect it to the rest of the workflow 

(indicator calculations, etc., which we will build in Steps 2-3). At the end of processing one ticker, you’ll 
loop back to the Split In Batches node to grab the next ticker. Typically, n8n’s Split In Batches node has 
a built-in loop: after the last node in the sequence, connect it back to Split In Batches (to the “Continue” 
input). This causes the workflow to iterate. Make sure to connect the Split In Batches’s “next” output (the 
one on the right side of the node) into the Google Sheets node, and then from the final node of ticker 
processing, connect back into Split In Batches’s “main” input (usually the top left of the node). This setup 
will sequentially execute the ticker list. 
1.4 Respecting Google API Rate Limits: 

 
 
 
 
 
 
 
 
 
 
 
Google Sheets API has strict quotas (for example, ~60 read requests per minute per user in some cases). 
If you have many tickers or are pulling a lot of data, you must avoid sending too many requests in a short 
time. n8n doesn’t automatically throttle, but offers tools to handle this: 

• 

Use a Wait Node: Insert an n8n Wait node inside the ticker loop to pause between API 
calls. For example, after the Google Sheets Read node (or right before it), add a Wait node set to wait 2 
seconds (2000 milliseconds). This will ensure at most one Google Sheets fetch every 2 seconds. In 
n8n’s forum, it’s suggested to use a Wait node in loops to throttle requests to Google Sheets. Two 
seconds is a reasonable starting point, but if you still hit limits, increase the delay. 

• 

Use Retry on Fail: On the Google Sheets node, under Settings, enable Retry On Fail. 
Set “Max Attempts” to a few (e.g., 3) and Wait Between Tries to a safe interval (if we expect 60 req/min 
limit, that’s 1 per second, so 2000ms between tries as well). This way, if a rate limit error (HTTP 429) 
occurs, n8n will automatically wait and retry the request. 

• 

Batch Your Data: Since Google Sheets can return many rows in one request (all data for 
a ticker in one go), we’re effectively minimizing requests by fetching all needed data in one call per ticker. 
Avoid fetching one row at a time or making unnecessary separate calls. Use the “Get Many Rows” 
operation to your advantage. 

• 

Monitor the n8n execution or Google API dashboard. If you see “Quota exceeded… too 

many requests” errors, increase the wait time or reduce frequency. Usually, with sequential processing 
and a small delay, you should stay within limits. 
At this point, you should have an n8n setup that can retrieve stock data from Google Sheets for one or 
more tickers safely. Now, let’s move on to calculating technical indicators on this data. 
Step 2: Calculating Technical Indicators (with Theory & Node Configuration) 
Now that we have raw price data in n8n, we’ll calculate various technical indicators. We will use Function 
nodes in n8n for these calculations. A Function node allows you to write JavaScript to manipulate the 
input data and produce output. Each indicator will be computed based on the historical data for each 
ticker. 
Before diving into each indicator, note a few best practices for calculations: 

• 

Ensure the price data is sorted by date (ascending or descending) consistently. If data 
from Google Sheets isn’t sorted, you may want to sort it first in a Function node (by date). This ensures 
moving averages or other rolling calculations use the correct order. 

• 

Many indicators require a certain number of periods before they start producing values 

(e.g., a 200-day SMA needs 200 data points). For the first N-1 days, you might not have a value – decide 
if you will output null/undefined or simply start outputting once available. In our code, we’ll typically start 
adding values only after we have enough data. 

• 

We will add new fields to the data (like a field “SMA20” for 20-day SMA, etc.). n8n’s 

Function node should return an array of items where each item’s JSON includes the original data plus 
these new fields. By returning the same number of items as input, joined with new properties, we maintain 
alignment by date. 
• 

We’ll handle potential missing values gracefully: if any input (like Volume or High/Low) is 
missing or non-numeric, the code should check and avoid NaN issues (we can default missing volume to 
0, for instance, or skip calculation if data is incomplete). 
We’ll address each indicator one by one, including the financial theory & interpretation, common 
pitfalls, the n8n node setup, and the JavaScript code to compute it. 
2.1 Simple & Exponential Moving Averages (SMA & EMA for 20, 50, 200 periods) 
Financial Theory: Moving Averages smooth out price data to reveal the underlying trend by averaging 
prices over a period. A Simple Moving Average (SMA) is the arithmetic mean of closing prices over the 
last N periods (days). For example, a 50-day SMA is the average close price of the past 50 days. Traders 
use SMAs to identify trend direction and potential support or resistance areas – in an uptrend, price often 
stays above a rising SMA, which acts as support; in a downtrend, price stays below a falling SMA, acting 

 
 
 
 
 
 
 
 
as resistance. Key SMAs like the 200-day are watched by institutions to judge long-term trend; if price is 
above the 200-day SMA, the asset is generally considered in an uptrend. The Exponential Moving 
Average (EMA) is similar but gives more weight to recent prices, making it respond faster to new price 
changes. EMAs are often used for shorter periods or by traders who want a more responsive indicator 
(e.g., a 20-day EMA reacts quicker to recent price moves than a 20-day SMA). Common periods we’ll 
compute: 20-day (roughly 1 month of trading), 50-day (quarterly trend), 200-day (about 40 weeks, 
long-term trend). We’ll do both SMA and EMA for each of these to compare slow vs. fast average. 
Professional Interpretation: 

• 

Daily timeframe: The 20-day MA often tracks the short-term trend. Traders might say if 

price is above the 20 EMA, momentum is bullish in the short term. The 50-day and 200-day are more 
significant: the 50-day vs 200-day crossover signals are famous (the “golden cross” when the 50-day 
SMA crosses above the 200-day SMA, signaling a potential major uptrend; the “death cross” when 50 
falls below 200, signaling a downtrend). Also, the 200-day itself is seen as a dividing line for long-term 
trend; institutions view dips to the 200-day as buying opportunities in bull markets or selling opportunities 
in bear markets. 
• 

Weekly timeframe: Some professionals also look at weekly moving averages (e.g., 

40-week = ~200-day). Weekly MAs filter out daily noise even more. A stock above its 40-week (200-day) 
on a weekly chart is strongly bullish. Weekly golden crosses are rarer but even more significant signals of 
trend changes. Because weekly data has fewer points, MAs there will update more slowly but indicate 
broader trends (good for long-term investors). 
Common Pitfalls & Best Practices: 

• 

Lagging Nature: Moving averages by design lag behind price. An SMA might make you 

late to catch a sudden trend change. That’s why faster MAs (like EMA or shorter periods) are used to 
complement slower ones. For example, a disadvantage of SMA is it might not reflect the latest price 
action if a sharp move happened (since old data is equally weighted). EMA addresses this by weighting 
recent data more, but the trade-off is EMAs can give more false signals on small fluctuations (more 
whipsaw). It’s common to use both: e.g., watch a 50-day SMA for overall trend but a 20-day EMA for entry 
timing. 

• 

Whipsaws in Sideways Markets: In a choppy, range-bound market, price might cross 

above and below moving averages frequently, triggering false trend signals. Be cautious of using MA 
crossovers blindly when there is no clear trend. One way to avoid this pitfall is to look at multiple MAs (like 
the slope of the 200-day – flat means no trend) or combine with other indicators (as we do in this 
workflow) to confirm. 

• 

Period Selection: 20, 50, 200 are traditional and generally effective. But different assets 

might trend on different timeframes. Some traders use 100-day as well. The exact number is less 
important than consistency and understanding what it represents (short vs intermediate vs long term 
trend). For our purposes, we’ll stick with the standard 20/50/200 which are widely used benchmarks. 

• 

Data Sufficiency: Make sure you have at least 200 data points to calculate the 200-day 

SMA; otherwise, the first 199 days won’t have a value. In our implementation, we will handle this by 
starting to output SMA200 only when we have 200 days. If your data is shorter than the period, consider 
not using that indicator or find a way to pad the data (not recommended – better to wait until enough data 
accrues). 
n8n Node Configuration: 
We will use a Function node called “Calc Moving Averages” (you can name it as you like). Connect the 
output of the Google Sheets node (which provides the OHLCV data for a ticker) into this Function node. In 
the Function node, we will: 

• 

Parse the Close prices from the input items (they might be strings from the sheet, so 

convert to Number). 

• 

Compute SMA for 20, 50, 200; compute EMA for 20, 50, 200. 

 
 
 
 
 
 
 
 
• 
• 

Add these values to each item’s JSON (for each date). 
Return the modified items. 

Full JavaScript Code (Function node: Calc Moving Averages): 
// Get all input data items (each item is one row with Date, Open, High, Low, Close, Volume, etc.) 
const itemsIn = items;  // items is an array of input objects { json: { ... } } 
if (itemsIn.length === 0) { 
  return [];  // no data, return empty 
} 
// First, extract the closing prices as numbers in an array for easy calculation: 
const closes = itemsIn.map(item => { 
  // Ensure the Close value is a number (Google Sheets might return it as a string) 
  const closeStr = item.json.Close || item.json.close || item.json.ClosePrice || item.json.close_price; 
  // Try a few possible key names; adjust based on your sheet's header. We assume "Close". 
  return closeStr !== undefined ? parseFloat(closeStr) : null; 
}); 
// We’ll prepare arrays for each indicator: 
const sma20 = [], sma50 = [], sma200 = []; 
const ema20 = [], ema50 = [], ema200 = []; 
// Helper function to calculate simple moving average for a given period. 
function calcSMA(values, period, index) { 
  // Calculate SMA ending at index (inclusive) over 'period' values 
  // i.e., average of values[index-period+1...index] 
  if (index < period - 1) { 
    return null; // not enough data points yet 
  } 
  let sum = 0; 
  for (let j = index; j > index - period; j--) { 
    sum += values[j]; 
  } 
  return sum / period; 
} 
// Helper for EMA: we’ll calculate EMA iteratively. 
// EMA formula: EMA_today = (Price_today * k) + (EMA_yesterday * (1 - k)), 
// where k = 2/(period+1). We need a start EMA (we can use SMA of first period as initial EMA). 
function calcEMASeries(values, period) { 
  const k = 2 / (period + 1); 
  const emaArr = []; 
  let emaPrev = null; 
  for (let i = 0; i < values.length; i++) { 
    if (i < period - 1) { 
      emaArr.push(null); // not enough data for full period 
      continue; 
    } 
    if (i === period - 1) { 
      // Base EMA on SMA for first period available 
      let sum = 0; 
      for (let j = 0; j < period; j++) { 
        sum += values[j]; 
      } 

 
 
      emaPrev = sum / period; 
      emaArr.push(emaPrev); 
    } else { 
      // EMA calculation for subsequent points 
      const price = values[i]; 
      emaPrev = (price * k) + (emaPrev * (1 - k)); 
      emaArr.push(emaPrev); 
    } 
  } 
  return emaArr; 
} 
// Calculate SMA series for each period by iterating through data: 
for (let i = 0; i < closes.length; i++) { 
  sma20.push(calcSMA(closes, 20, i)); 
  sma50.push(calcSMA(closes, 50, i)); 
  sma200.push(calcSMA(closes, 200, i)); 
} 
// Calculate EMA series using the helper (which returns full array): 
const ema20Arr = calcEMASeries(closes, 20); 
const ema50Arr = calcEMASeries(closes, 50); 
const ema200Arr = calcEMASeries(closes, 200); 
// Now attach these to the items 
const outputItems = itemsIn.map((item, index) => { 
  item.json.SMA20 = sma20[index]; 
  item.json.SMA50 = sma50[index]; 
  item.json.SMA200 = sma200[index]; 
  item.json.EMA20 = ema20Arr[index]; 
  item.json.EMA50 = ema50Arr[index]; 
  item.json.EMA200 = ema200Arr[index]; 
  return item; 
}); 
return outputItems; 
Explanation of the Code: We create arrays for close prices and then fill SMA and EMA arrays. For SMA, 
we explicitly average the last N values for each day (this is O(N^2) in worst case, but with at most a few 
thousand trading days it’s fine; for huge data sets, one would optimize by running sum). For EMA, we use 
the smoothing factor formula (Wilder’s method). We seed the EMA on the first available full period by 
using an SMA as the initial value (common practice), then apply the EMA formula. Each item in output 
gets new fields (SMA20, etc.). If an indicator isn’t available for that date (null), it stays null – e.g., the first 
199 days will have SMA200 = null. 
After this node, each item (each date in the price history) has additional fields for the moving averages. 
These will be used later for generating signals (and you could also write them to the sheet if needed). For 
example, on the latest date item, item.json.SMA50 and item.json.SMA200 can be compared to see trend 
direction or crossovers. 
(Optional) Verify outputs: You can test this node by executing it (with the previous Google Sheets node 
feeding it data). In the node’s output, pick a date and manually verify one of the calculations (e.g., check 
that SMA20 equals the average of the Close of that date and the 19 preceding days). If something looks 
off, check that the Close prices were parsed correctly (no NaNs). The code above assumes the sheet’s 
column is exactly named “Close”. If your column name was different, adjust item.json.Close accordingly 
or use item.json["YourColumnName"]. 

2.2 Relative Strength Index (RSI – 14 period) 
Financial Theory: The Relative Strength Index (RSI) is a momentum oscillator that measures the 
magnitude of recent gains vs. losses to identify overbought or oversold conditions. RSI values range from 
0 to 100. Classic interpretation: an RSI above 70 suggests the asset is overbought (price rose too far, 
potentially due for a pullback), while RSI below 30 suggests oversold (price fell too far, could bounce). 
Traders use RSI to time entries/exits: for example, an RSI that drops below 30 then rises back above it 
can be a buy signal (the “oversold” condition is ending). Conversely, RSI crossing below 70 from above 
can be seen as a sell signal. RSI around 50 is mid-range; some professionals treat RSI>50 as generally 
bullish momentum, <50 bearish (especially useful when combined with trend analysis). The default period 
is 14 days as introduced by J. Welles Wilder Jr., who created the RSI. 
Professional Interpretation: 

• 

Daily RSI: Many traders use daily 14-day RSI for swing trading. A common strategy: buy 

when RSI < 30 (oversold) and then rises back above 30; sell or take profit when RSI > 70 and then falls 
below 70. Another advanced use is RSI divergence: if price makes a new low but RSI makes a higher 
low, it’s a bullish divergence – momentum loss on the downside hinting at a reversal. Similarly, new price 
high but RSI lower high is bearish divergence. These can precede trend changes. Also, institutional 
traders sometimes adjust RSI thresholds based on trend: in a strong uptrend, RSI might oscillate mostly 
between 40 and 80 (never getting to 30), so an RSI dipping to ~40 could already be a buy zone – the 
30/70 rule isn’t absolute. In downtrends, RSI might regularly peak at 60 instead of 70. So context matters: 
if weekly trend is up, you might treat RSI 40 as “oversold” relative to that uptrend. 

• 

Weekly RSI: Using RSI on a weekly chart (i.e., 14-week RSI) gives a longer-term 

momentum view. It moves more slowly and will rarely swing to extremes unless a major multi-month 
move happened. A high weekly RSI (e.g., >70) might indicate an overextended market on a big-picture 
scale (perhaps due for a correction in coming weeks). Weekly RSI staying above 50 indicates strong 
positive momentum in the long run. Some backtesting studies show that daily RSI can give more frequent 
signals, whereas weekly RSI gives fewer but perhaps more reliable, albeit with larger drawdowns if 
wrong. If your strategy is long-term, you might incorporate weekly RSI to filter trades (e.g., only buy if 
weekly RSI is not overbought even if daily is). In this guide, we’ll focus on daily RSI in the calculations, but 
the concepts apply similarly if you ever use weekly data. 
Common Pitfalls & Best Practices: 

• 

Overbought vs. Trend: New traders often mistake “overbought” to mean “price will 

immediately drop.” In reality, if a strong uptrend is underway, RSI can remain overbought ( >70) for a long 
time while price keeps climbing. Selling just because RSI > 70 in a roaring bull market can make you exit 
too early. The proper use is to watch for RSI to climb into extreme and then cross back out or show 
divergence as confirmation. Similarly, oversold can stay oversold in a crash. Always consider the trend 
context – e.g., if the 200-day SMA is strongly upward (bullish), you might treat an RSI dip to 30 as a 
buying opportunity rather than a reason to short. 

• 

Different Settings: The default 14 is standard, but day traders sometimes use 7 or 9 for 
more sensitivity, and long-term investors might use 20 or 30 for smoothness. Our 14-day will suffice for a 
broad analysis. 
• 

Calculation details: RSI calculation has a specific formula involving average gains and 

losses. We’ll implement Wilder’s smoothing method (which is common in most trading platforms) to get an 
accurate result. One pitfall is not doing the smoothing (just doing simple average of last 14 up vs down 
moves) – that can make your RSI deviate slightly from typical values. Wilder’s method is an 
exponential-like smoothing which we will use. 

• 

Ensure continuous data: RSI uses consecutive differences. If your data has gaps 

(missing days), usually it’s fine (weekends for stocks, etc., RSI just considers each consecutive available 
point). Just be careful if your sheet has missing values or zeros; treat them appropriately (e.g., if Volume 

 
 
 
 
 
 
is 0 on a holiday, there was no trading – maybe skip that day’s calculation or copy the previous day’s 
close to avoid a giant false drop). 
n8n Node Configuration: 
Add another Function node and name it “Calc RSI”. Connect it after the Moving Averages node (so it 
receives items with the Close prices and MAs, though it really only needs Close to compute RSI). The 
reason to separate nodes is clarity; you could combine with the MA calculation code, but keeping them 
modular is easier to read. This Function will: 

• 
• 

Take the close price series and compute the 14-day RSI for each day. 
Add a new field, say RSI14, to each item. 

We use 14 by default, but you could expose the period as a variable if needed. We’ll implement Wilder’s 
RSI: 

• 
• 
• 

Calculate the price change (delta) for each day (today’s close minus yesterday’s close). 
Separate into gains (positive deltas) and losses (negative deltas). 
The first RSI value (on the 14th data point) will use simple average of gains over 14 

days and simple average of losses over 14 days, then RSI = 100 – 100/(1 + RS) where RS = 
avgGain/avgLoss. 
• 

Subsequently, use a smoothed approach: 

avgGain_today = (prevAvgGain * 13 + currentGain) / 14 
avgLoss_today = (prevAvgLoss * 13 + currentLoss) / 14 

• 

Then RS = avgGain/avgLoss, RSI = 100 – 100/(1+RS). If avgLoss is 0, RSI = 100 

(meaning no losses in the period -> extremely strong); if avgGain is 0, RSI = 0 (no gains -> extremely 
weak). Typically, if avgLoss = 0, we set RSI 100, and if avgGain = 0, RSI 0, to avoid division by zero. 
Full JavaScript Code (Function node: Calc RSI): 
const inputItems = items; 
if (inputItems.length === 0) { 
  return []; 
} 
const closes = inputItems.map(item => parseFloat(item.json.Close)); 
const period = 14; 
const rsiArray = []; 
// Arrays to hold average gain and loss for each day (for debugging or reference) 
let avgGain = 0; 
let avgLoss = 0; 
for (let i = 0; i < closes.length; i++) { 
  if (i === 0) { 
    // first data point, no previous day to compare 
    rsiArray.push(null); 
    continue; 
  } 
  const change = closes[i] - closes[i-1]; 
  const gain = change > 0 ? change : 0; 
  const loss = change < 0 ? -change : 0; 

  if (i < period) { 
    // For first 1 to 13 (if period=14), we don't have full period yet 
    // We will just push null until i == 13 (14th point, index 13) 
    if (i < period - 1) { 
      rsiArray.push(null); 
      // accumulate gains/losses for initial average 

 
 
 
 
 
 
 
   
      avgGain += gain; 
      avgLoss += loss; 
      continue; 
    } else if (i === period - 1) { 
      // at the 14th day (index 13), compute the initial average gain/loss 
      avgGain = (avgGain + gain) / period; 
      avgLoss = (avgLoss + loss) / period; 
      // Now compute initial RSI 
      const rs = avgLoss === 0 ? Infinity : avgGain / avgLoss; 
      const rsi = avgLoss === 0 ? 100 : (avgGain === 0 ? 0 : (100 - (100 / (1 + rs)))); 
      rsiArray.push(parseFloat(rsi.toFixed(2))); 
      continue; 
    } 
  } else { 
    // For days beyond the initial period, use Wilder’s smoothing: 
    avgGain = ((avgGain * (period - 1)) + gain) / period; 
    avgLoss = ((avgLoss * (period - 1)) + loss) / period; 
    const rs = avgLoss === 0 ? Infinity : avgGain / avgLoss; 
    const rsi = avgLoss === 0 ? 100 : (avgGain === 0 ? 0 : (100 - (100 / (1 + rs)))); 
    rsiArray.push(parseFloat(rsi.toFixed(2))); 
  } 
} 
// Attach RSI to items 
return inputItems.map((item, index) => { 
  item.json.RSI14 = rsiArray[index]; 
  return item; 
}); 
Explanation: We iterate through close prices calculating gains/losses. Until we have 14 days, we collect 
initial sums. At the 14th day, compute the first RSI via simple average. After that, we update average 
gain/loss with smoothing (which essentially is an EMA on the gains and losses). We round the RSI to 2 
decimals for neatness (optional). The result: each item from index 13 onward will have an RSI14 value 
(indices 0-12 will be null because 14-day RSI can’t be computed for the first 13 days). 
Best Practices in RSI Code: 
We handled division by zero: if avgLoss becomes 0 (meaning no losses in the last 14 days – very strong 
uptrend), we set RS to Infinity and RSI to 100 (or technically 100 - 100/(1+∞) = 100). If avgGain is 0 (no 
gains in period – downtrend), RSI = 0. In between, RSI will oscillate between 0 and 100. Typically, values 
> 70 and < 30 are our extreme zones of interest. 
Interpreting RSI output: 
Later, we will use item.json.RSI14 to generate signals. Generally: 

• 
entries). 
• 
• 

RSI14 > 70 might be flagged as overbought (sell condition, or at least caution long 

RSI14 < 30 flagged oversold (potential buy condition). 
RSI crossing above 50 could be used to confirm momentum turning up, crossing below 

50 momentum down. Some strategies incorporate the 50-level as a filter (for instance, only take buy 
signals if RSI is above 50, meaning momentum is on your side). 

• 

We could also incorporate an RSI divergence check in an advanced strategy, but that 

requires looking at past values relative to price changes, which is more complex and beyond our scope 
here. 

 
 
 
 
For our multi-indicator strategy, we might simply use RSI thresholds or changes (like if yesterday RSI < 30 
and today RSI > 30, that’s a bullish short-term reversal signal). 
Now with RSI computed, our items have fields: Date, Open, High, Low, Close, Volume, SMA20/50/200, 
EMA20/50/200, RSI14. Next, MACD. 
2.3 Moving Average Convergence Divergence (MACD, with signal line & histogram) 
Financial Theory: MACD (Moving Average Convergence/Divergence) is a trend-following momentum 
indicator that shows the relationship between two EMAs of prices. The classic MACD line is the 12-period 
EMA minus the 26-period EMA (using closing prices). A positive MACD value means the short-term 
average (12) is above the long-term average (26), indicating upward momentum; a negative MACD 
means 12 below 26, indicating downward momentum. Along with the MACD line, a signal line (often 
9-period EMA of the MACD line) is plotted. When the MACD line crosses above the signal line, it’s a 
bullish crossover (often interpreted as a buy signal); when MACD crosses below the signal, it’s a 
bearish crossover (a sell signal). The MACD histogram is the difference between MACD line and 
signal line – it visualizes the convergence/divergence: if histogram is above zero and growing, the bullish 
momentum is increasing; if it’s below zero and falling further, bearish momentum is increasing. MACD is 
one of the most popular indicators, often used with default (12, 26, 9) on daily charts. 
Professional Interpretation: 

• 

Daily MACD: Traders watch for MACD crossovers as early signals of trend shifts. For 

example, after a pullback in an uptrend, a MACD bullish crossover (MACD line crosses up through signal) 
can signal the end of the pullback and a good entry point. Conversely, if a stock had a big run-up and then 
MACD crosses down (MACD below signal), it might warn of a trend change to the downside or at least a 
consolidation. Another key signal is the centerline crossover: when MACD itself crosses above zero, 
that confirms a shift to bullish trend (short-term average now above long-term). Many trading systems 
require MACD > 0 to consider long trades, and MACD < 0 for shorts. Also, MACD divergence: if price 
makes a higher high but MACD makes a lower high, it indicates waning momentum (potential bearish 
reversal coming). Similarly, lower lows in price vs higher lows in MACD can precede bullish reversals. 

• 

Weekly MACD: On weekly data, MACD (12-week, 26-week, 9-week) is slower but can 
help filter out noise. A weekly MACD bullish crossover can signal a multi-month rally might be starting, 
and a weekly bearish crossover might signal a major top. Some long-term investors use weekly MACD to 
stay with big trends and avoid whipsaws. However, note that standard 12/26 on weekly means ~125 = 60 
trading days and 265 = 130 trading days EMA, roughly 3 and 6 months – so it’s capturing a half-year 
trend. It’s quite smooth. For our purposes, we’ll stick to daily MACD for signals, but you can experiment 
with weekly for confirmation. 
Common Pitfalls & Best Practices: 

• 

Whipsaws in Ranges: MACD, like moving averages, works best when the market is 
trending . In a sideways, range-bound market, MACD lines will cross back and forth frequently without 
meaningful price moves, generating false signals. To avoid this, many traders either avoid MACD signals 
unless price is above some moving average (indicating a trend) or combine MACD with other filters (like 
we do). 

• 

Lag vs. Sensitivity: The standard 12,26,9 is a balance of smoothing. You can adjust 

these if you find signals are too late/too early. Shorter EMAs (e.g., 5,35 for MACD or a shorter signal line) 
will give earlier signals but more noise. Longer will be very smooth but slow. We will use standard settings 
as they are widely accepted. 

• 

Histogram interpretation: Many traders focus on the histogram for early clues. For 

example, when a trend is strong, MACD histogram will peak and then start to shrink even before the lines 
cross – that shrinking indicates convergence (momentum slowing). A common tactic: if histogram has 
been positive but starts declining towards zero, it may warn the bullish momentum is fading (even before 
an actual bearish crossover happens). Similarly, an improving negative histogram can hint at a bullish turn 
soon. Using histogram can be advanced, but it’s good to be aware of. 

 
 
 
 
 
• 

Zero line importance: As mentioned, MACD above zero confirms bullish trend, below 

zero bearish. Sometimes traders wait for both a line crossover and crossing the zero line to be extra sure. 
In our strategy, we might incorporate MACD in a simpler way (like “MACD is positive and above signal” as 
bullish condition). 
n8n Node Configuration: 
Add another Function node named “Calc MACD”. Connect it after the RSI node. This Function will: 

• 
• 

Use the close prices again to calculate: 
EMA12 and EMA26 for each day (we can reuse our EMA helper or code from above, or 

recalc fresh here for clarity). Alternatively, since we already calculated EMA20,50,200, we didn’t 
specifically calculate 12 and 26 in the earlier node. We’ll do it here. 

• 
• 
• 
• 

MACD line = EMA12 – EMA26 for each day. 
Signal line = 9-day EMA of the MACD line. 
Histogram = MACD – Signal. 
Add these as fields, e.g., MACD, MACD_Signal, MACD_Histogram to each item. 

We must ensure not to compute MACD until we have at least 26 days of data (since EMA26 needs that 
many to start meaningfully). We may start MACD output from day 26 or 27 onward. 
We can leverage the EMA calculation code from the MA node. To avoid duplication, one approach is: in 
the “Calc Moving Averages” node, we could have also calculated EMA12 and EMA26 and passed them. 
But to keep nodes focused, we’ll just recalc quickly here (12 and 26 are short, performance isn’t a 
concern). 
Full JavaScript Code (Function node: Calc MACD): 
const inputItems = items; 
if (inputItems.length === 0) { 
  return []; 
} 
const closes = inputItems.map(item => parseFloat(item.json.Close)); 
// Function to get EMA series for a given period (similar to earlier EMA function) 
function getEMA(values, period) { 
  const k = 2 / (period + 1); 
  const emaArr = []; 
  let emaPrev; 
  for (let i = 0; i < values.length; i++) { 
    if (i === 0) { 
      // start EMA at first price to avoid nulls in beginning (or we could start at period-1 with SMA, but it’s 
fine to initialize at first value for longer EMA to settle) 
      emaPrev = values[i]; 
      emaArr.push(emaPrev); 
    } else { 
      emaPrev = (values[i] * k) + (emaPrev * (1 - k)); 
      emaArr.push(emaPrev); 
    } 
  } 
  return emaArr; 
} 
// Calculate EMAs for 12 and 26 
const ema12 = getEMA(closes, 12); 
const ema26 = getEMA(closes, 26); 
// Now MACD line and signal 
const macdLine = [];  // EMA12 - EMA26 

 
 
 
 
 
 
 
for (let i = 0; i < closes.length; i++) { 
  const macdVal = ema12[i] - ema26[i]; 
  macdLine.push(macdVal); 
} 
// Calculate signal line (9-period EMA of macdLine) 
const signalLine = getEMA(macdLine, 9); 
// Calculate histogram = macdLine - signalLine 
const histogram = macdLine.map((val, idx) => val - (signalLine[idx] || 0)); 
// Attach to items 
return inputItems.map((item, index) => { 
  item.json.MACD = parseFloat(macdLine[index].toFixed(4));         // MACD line 
  item.json.MACD_Signal = parseFloat(signalLine[index].toFixed(4)); // Signal line 
  item.json.MACD_Hist = parseFloat(histogram[index].toFixed(4));    // Histogram 
  return item; 
}); 
Explanation: We compute EMA12 and EMA26 for the entire series. We start EMA at the first data point 
to avoid a bunch of leading nulls – this introduces a slight inaccuracy for the first 25 values, but practically 
it will settle after a couple of weeks. (If you want absolute precision, you could start at day 26 with initial 
SMA for EMA26, but it’s not critical; MACD is anyway not used until a bit into data typically). Then MACD 
line = ema12 - ema26. Then signal = EMA9 of MACD line. Then histogram. We toFixed(4) just to make 
numbers neat (MACD often is small, e.g., 0.5, etc., 4 decimal places is plenty). 
We add fields: 

• 
• 
• 

MACD (the value of MACD line), 
MACD_Signal (value of signal line), 
MACD_Hist (histogram). 

Usage & Verification: After running this node, check the last item (most recent date). If the Close price 
increased in the last days, MACD should be positive, etc. You can verify a couple of known points: e.g., 
on the day where Close first rises significantly after a slump, MACD might cross above signal. If you have 
access to a chart, verify our values roughly match (with some tolerance due to our initial seeding 
approach, the first few values might differ slightly from a charting tool, but later ones should match well). 
Pitfall Check: If the stock had a long sideways period, MACD might be hovering near zero and crossing 
often – just be aware, that’s where we need other filters. If data is short (< 26 days), MACD for early items 
may not be meaningful; but our code will still output something (because we start EMA at first value, 
MACD starts at 0 on first day since ema12 = ema26 = price). If that’s undesirable, you could set 
item.json.MACD = null for index < 26 to indicate no reliable MACD yet. For a robust system, maybe do: 
if (index < 26) { 
    item.json.MACD = null; item.json.MACD_Signal = null; item.json.MACD_Hist = null; 
} else { ...assign values... } 
But it’s optional. 
Now we have MACD values for each date. 
2.4 Bollinger Bands (20-day SMA, ±2 std dev) and Bollinger Band Width 
Financial Theory: Bollinger Bands consist of a middle band (typically a 20-day SMA of price) and an 
upper and lower band calculated as the standard deviation of price over those 20 days, multiplied by a 
factor (usually 2) and added/subtracted from the middle . The result is an envelope around price that 
expands and contracts with volatility . Key interpretations: when bands are narrow (low volatility), it often 
precedes a large move (this is called a squeeze – a volatility contraction that tends to resolve with a 
breakout). When bands are wide, volatility is high; after extreme volatility, bands may contract as things 
calm down. Bollinger Bands also give an idea of relative price – if price touches the upper band, it is high 
relative to the recent average (potentially overbought); touching the lower band means price is low 

 
 
 
relative to recent average (potentially oversold). Traders sometimes use this for mean reversion trades: 
e.g., if price tags the upper band, they look for a sell if there’s confirmation of a pullback; conversely, price 
at lower band might be a buy if it bounces. However, in strong trends price can “ride the band” (stay near 
an upper band during a powerful uptrend), so one must confirm with trend indicators or patterns. The 
Band Width (or BB Width) is just (UpperBand - LowerBand) – it reflects volatility. Some define a %B or 
normalized width, but for simplicity, raw width or comparing widths over time is fine: a very low width 
(relative to past widths) indicates a volatility squeeze. 
Professional Interpretation: 

• 

Using Bollinger Bands: One strategy is the Bollinger Band squeeze breakout: when 

you see historically tight bands (often you can observe when band width is at multi-month lows), expect a 
big move. Traders then watch for a breakout beyond the bands: e.g., price closing above the upper band 
on high volume after a squeeze can signal start of a strong uptrend, and vice versa for breakdown. 
Another approach: in range markets, use the Bollinger Bounce – price tends to revert to the mean 
(middle band) after hitting extreme. For example, if price touches the lower band and shows a bullish 
candle, one might buy expecting a move back toward the middle or upper band. In trending markets, the 
middle band (20 SMA) itself becomes a support line – e.g., in an uptrend, when price pulls back toward 
the middle band and then turns up, it’s often a good entry; the lower band in that case might be an 
ultimate stop level. On weekly timeframes, Bollinger Bands can highlight long-term volatility cycles. 

• 

Bollinger Band Width: Professionals often look at Band Width indicator to quantify 

volatility. A high BB width means very volatile (maybe avoid entering new trades as it may be near a 
climax), whereas an ultra-low BB width means consolidation (get ready for a breakout trade). John 
Bollinger (the creator) often mentioned that periods of low volatility are usually followed by periods of high 
volatility and vice versa. He even defined %b (where current price is relative to bands) and Band Width 
indicators for systematic use. In practice, we might say “Band width is lowest in 6 months, prepare for a 
breakout” or “Band width is extremely high, volatility may revert soon.” 
Common Pitfalls & Best Practices: 

• 

Not a Standalone Signal: A common mistake is to short just because price touches 

upper band or buy because it touches lower band. As mentioned, in a strong trend price can walk along 
the upper band – selling there would have you shorting into an uptrend. Bollinger Bands should be 
combined with other evidence: e.g., at upper band, check if RSI is overbought or a bearish candlestick 
forms; at lower band, see if there’s bullish divergence, etc. In our multi-indicator strategy, Bollinger signals 
will be tempered by trend and momentum indicators. 

• 

Adjusting Settings: Standard is 20-day and 2 std deviations. That captures ~95% of 

price action if it were normally distributed. You can widen to 2.5 std for less frequent signals or narrow to 
1.5 std for more signals. 20-day is a default; some use 20-day on daily but 20-week on weekly; others 
experiment with 10-day for short-term trades. We will stick to 20, 2 for now, as it’s well-tested. 

• 

Clumping of signals: In a low volatility period, you may get multiple band touches with 

little result. E.g., price ping-pongs between the narrow bands. It can be frustrating; often the real move 
comes after multiple false starts. To handle this, require confirmation like volume expansion on the break 
or multiple indicators aligning (which we’ll do). 

• 

Mean reversion vs. Breakout: Understand what regime the market is in. If it’s ranging, 
playing the bounce off bands is fine. If it’s trending, play breakouts or pullback entries near middle band 
instead. Sometimes a band breakout is the start of a trend, not an immediate mean reversion, so adapt 
accordingly. We will use band info mainly for volatility (to know if we should expect a breakout) and 
maybe as an overbought/oversold factor in signals. 
n8n Node Configuration: 
Add “Calc BollingerBands” Function node, connect after MACD node. This will: 

 
 
 
 
 
 
• 

Compute the 20-day SMA of closes (we actually already have SMA20 from our earlier 

calculation – we can reuse that instead of recalculating). We can trust the SMA20 field. If you prefer not 
relying on previous node’s data, you could recompute here, but let’s use it. 

• 

Compute the 20-day standard deviation of close prices for each day. Standard deviation 

formula: sqrt(mean of squared deviations from mean). Since we have a rolling window, for each index i 
from 19 onward: take closes[i-19…i], find their mean (that is SMA20 we have), then calculate std = 
sqrt(sum((close_j - SMA20)^2)/20). 

• 
• 

Upper band = SMA20 + (2 * std), Lower band = SMA20 - (2 * std). 
Band width = Upper - Lower. (We can also output a normalized version like 

(Upper-Lower)/SMA20 if desired, but not necessary). 

• 

Add fields: BB_upper, BB_middle, BB_lower, BB_width. (Middle is basically SMA20 

again, but we can include for completeness or clarity). 
We will utilize existing item.json.SMA20 from our data (ensuring that the moving averages node has 
indeed run before this – which it has in our sequence). One thing: if someone disables the MA node or if 
data flows directly here, then SMA20 might not exist. To be safe, we could compute if not present. But 
assuming our workflow is intact, SMA20 is there. 
Full JavaScript Code (Function node: Calc BollingerBands): 
const inputItems = items; 
if (inputItems.length === 0) { 
  return []; 
} 
// We will use the close price and SMA20 from each item. 
for (let i = 0; i < inputItems.length; i++) { 
  const item = inputItems[i]; 
  const closeVal = parseFloat(item.json.Close); 
  // Ensure we have SMA20 (if not, compute it quick here, but ideally it’s present) 
  let sma20 = item.json.SMA20; 
  if (sma20 === undefined || sma20 === null) { 
    // Compute SMA20 for this index (fallback calculation) 
    if (i >= 19) { 
      let sum = 0; 
      for (let j = i-19; j <= i; j++) { 
        sum += parseFloat(inputItems[j].json.Close); 
      } 
      sma20 = sum / 20; 
    } else { 
      sma20 = null; 
    } 
  } 

  if (sma20 === null) { 
    // not enough data for bands yet 
    item.json.BB_middle = null; 
    item.json.BB_upper = null; 
    item.json.BB_lower = null; 
    item.json.BB_width = null; 
  } else { 
    // Calculate standard deviation over last 20 closes 
    let sumSqDiff = 0; 

 
 
 
 
 
   
    for (let j = i-19; j <= i; j++) { 
      const cj = parseFloat(inputItems[j].json.Close); 
      sumSqDiff += Math.pow(cj - sma20, 2); 
    } 
    const variance = sumSqDiff / 20; 
    const stdDev = Math.sqrt(variance); 
    const upper = sma20 + 2 * stdDev; 
    const lower = sma20 - 2 * stdDev; 
    item.json.BB_middle = parseFloat(sma20.toFixed(4)); 
    item.json.BB_upper = parseFloat(upper.toFixed(4)); 
    item.json.BB_lower = parseFloat(lower.toFixed(4)); 
    item.json.BB_width = parseFloat((upper - lower).toFixed(4)); 
  } 
} 
return inputItems; 
Explanation: For each item from index 19 onward, we compute std dev using the previous 19 data plus 
current (total 20). We use SMA20 (the middle band) in the calculation. If i < 19, we can’t compute (not 
enough data), so we set bands to null for those early days. The result: each item from day 20 onwards 
has BB_middle, BB_upper, BB_lower, BB_width. Band width is just upper minus lower (so effectively 4 * 
std dev). 
Interpreting Bollinger output: We might use: if Close is near BB_upper and perhaps RSI is overbought, 
that’s a potential sell signal. If Close is near BB_lower and RSI oversold, potential buy. Also, look at 
BB_width: if it’s very low relative to its history, that suggests a squeeze; we might incorporate that by 
requiring a breakout confirmation with volume later. In our final signal logic, we might not use BB_width 
explicitly for a yes/no, but you might note it for context or maybe to weight the signal strength (e.g., a 
breakout signal coming after a low BB_width might be given extra weight). For simplicity, we might just 
output it for the user to see volatility. 
Now, we have covered trend (MAs), momentum (RSI, MACD), volatility (Bollinger). Next, volume and 
support/resistance and other oscillators. 
2.5 Volume Analysis and Confirmation 
Financial Theory: Volume represents the number of shares (or contracts) traded in a period. It is a 
crucial but often secondary indicator – it doesn’t tell direction by itself, but confirms the strength of price 
moves. High volume means lots of participation and conviction; low volume means weak participation. 
Key volume principles used by professionals: 

• 

Trend Confirmation: In an uptrend, you want to see volume rising on up days – “volume 

confirms price.” If price is making new highs on increasing volume, the trend is healthy. If price rises but 
volume declines, it may indicate dwindling buying interest (trend weakness). Similarly, in a downtrend, 
volume rising on down days confirms strong selling. 

• 

Volume Spikes & Exhaustion: A sudden huge volume spike can mark climax of a 

move. For example, after a sustained rally, an extremely high volume day might indicate everyone rushed 
in (often the last buyers) and the trend may soon exhaust. Same for panic selling at bottoms – a volume 
climax can mean sellers are exhausted. This is context-dependent but notable. 

• 

Volume on Breakouts: For a price breakout from a chart pattern or a resistance level, 

high volume on the breakout day is taken as confirmation that the breakout is real (lots of buyers behind 
it). A breakout on low volume is suspect – it may fail as not enough participants are supporting the move. 

• 

Volume Divergence: If volume is not following the trend (e.g., price keeps rising but 
volume each day is lower and lower), it could warn of a reversal. Or if price is falling to new lows but 
volume is not increasing, maybe the down move lacks enthusiasm and could reverse. 
Professional Interpretation: 

 
 
 
 
• 

Volume Moving Average: Analysts often look at volume relative to its average (say 

20-day avg volume). For instance, “today’s volume is 2x the average – something significant happened.” 
They also gauge accumulation/distribution by looking at volume on up days vs down days. 

• 

Volume and Patterns: Many chart patterns (like head-and-shoulders, triangles) explicitly 
consider volume (e.g., a head-and-shoulders is said to have lower volume on the head’s rally than the left 
shoulder rally, indicating waning demand). While we won’t delve into patterns, know that volume is a 
cornerstone for confirming any technical signal. 

• 

Weekly Volume: Weekly volume data (sum of volume in a week) can filter out daily noise 
(like a single day’s news spike). If a breakout is valid, you might see the week ending with above-average 
volume overall. 
• 

Volume Indicators: There are also volume-based indicators like OBV (On-Balance 

Volume) and MFI (Money Flow Index) that combine price and volume, but here we’ll just use raw volume 
analysis and a moving average of volume. 
Common Pitfalls & Best Practices: 

• 

Ignoring Volume: Some traders focus only on price indicators and ignore volume – this 

can be a mistake as volume often precedes price or warns when an indicator signal might be false. For 
example, RSI might flash overbought, but if it’s on extremely high volume up day (meaning strong buying 
force), shorting might still be dangerous. We incorporate volume to avoid such pitfalls. 

• 

One-day anomalies: Sometimes volume spikes due to non-technical reasons (index 
rebalancing, block trades, etc.). You might see an abnormal volume day that doesn’t correspond to a 
meaningful price move. These can distort averages. It’s okay – one can either manually adjust or be 
aware that one outlier can raise the average for 20 days and so on. Over a large dataset, not a big issue. 

• 

Relative to history: Always think of volume relative to recent history. A million shares 

might be huge for a thinly traded stock but nothing for a large-cap. That’s why a volume moving average 
is useful – it normalizes to that stock’s own activity. We’ll likely compute a 20-day volume average and 
maybe compare today’s volume to it. 

• 

Volume confirmation filter: In strategy, a prudent practice is to require volume 

confirmation for breakouts – e.g., if our other indicators say “Buy” but volume is below average, maybe 
don’t trust it fully (could be a false breakout). We will include such logic in the signal generation. 
n8n Node Configuration: 
Add a Function node “Calc VolumeStats” after Bollinger. In this, we’ll compute: 

view). 

• 

• 
• 

20-day average volume (and maybe also 50-day average, but let’s do 20 for shorter-term 

Maybe a volume ratio: today’s volume / average volume. 
We could also identify the highest volume in last N days (volume spike detection). Or 

simpler: mark if today’s volume > 1.5 * avgVolume (significant spike). 

We’ll add fields: VolAvg20, VolRatio and maybe a boolean like VolSpike if volume > some 

• 
threshold. 
Volume in the sheet likely is numeric (but might be string, convert to float). We also ensure to handle 
missing or zero volume (shouldn’t happen for a trading day unless it’s a holiday row – ideally those aren’t 
in sheet; if they are, maybe filter out days with zero volume as no trading). 
Full JavaScript Code (Function node: Calc VolumeStats): 
const inputItems = items; 
if (inputItems.length === 0) { 
  return []; 
} 
// Compute 20-day average volume for each day 
const volumes = inputItems.map(item => parseFloat(item.json.Volume || item.json.volume || 0)); 
const volAvg20 = []; 

 
 
 
 
 
 
 
 
 
 
 
 
for (let i = 0; i < volumes.length; i++) { 
  if (i < 19) { 
    volAvg20.push(null); 
  } else { 
    let sum = 0; 
    for (let j = i-19; j <= i; j++) { 
      sum += volumes[j]; 
    } 
    volAvg20.push(sum / 20); 
  } 
} 
// Mark volume spike if today's volume is > 1.5x average (you can adjust factor) 
const volSpike = volumes.map((vol, idx) => { 
  const avg = volAvg20[idx]; 
  if (avg !== null && vol > 1.5 * avg) { 
    return true; 
  } else { 
    return false; 
  } 
}); 
// Attach volume stats 
return inputItems.map((item, index) => { 
  item.json.VolAvg20 = volAvg20[index] !== null ? Math.round(volAvg20[index]) : null;  // round to nearest 
whole, since volume is usually integer 
  item.json.VolRatio = volAvg20[index] !== null ? parseFloat((volumes[index] / volAvg20[index]).toFixed(2)) 
: null; 
  item.json.VolSpike = volSpike[index]; 
  return item; 
}); 
Explanation: We compute a simple moving average of volume (20-day). Then for each day we check if 
volume > 1.5 * avg20 -> mark VolSpike true/false. We also give VolRatio (e.g., 2.0 means volume is 200% 
of average, 0.5 means half of average). We round average to nearest whole number for readability. 
We chose 1.5 as a threshold for “spike” – this is subjective; you could use 2.0 for stricter or 1.2 for looser. 
1.5 means 50% above normal, which is notable. The idea: if VolSpike is true and price is breaking out, 
that’s a very good sign. If a breakout has VolSpike false (below-average vol), we may distrust it. 
Using Volume in Signals: In the next step (signal generation), we’ll use these volume stats. For 
example: 
• 

If we have a buy signal condition (say moving averages and RSI agree), we might 

require either VolSpike true or at least not ridiculously low volume. We could also incorporate volume by 
saying if volume is higher than average and price moved, give extra weight to the signal (like signal 
strength). Conversely, if volume is very low, maybe reduce the signal strength or ignore borderline 
signals. 
Now, on to support & resistance. 
2.6 Support & Resistance Level Identification 
Financial Theory: Support and Resistance are price levels or zones where buying or selling pressure, 
respectively, tends to halt a price move. Support is a level where a downtrend might pause due to 
demand (buyers step in) ; Resistance is where an uptrend might pause due to supply (sellers take profit 
or short-sellers enter) . These levels often form at previous swing highs or lows: e.g., a past low that held 
could act as future support on a pullback . Support/resistance can also be dynamic (like moving averages 

 
we discussed can act as support/resistance) or diagonal (trendlines). For our algorithmic approach, we’ll 
focus on horizontal support/resistance derived from recent price history. 
Professional Interpretation: 

• 

Traders often draw horizontal lines at major swing highs and lows on a chart. For 

example, if a stock repeatedly could not fall below $50 (bounced off $50 several times), $50 is a strong 
support. If it repeatedly fails to rise above $60, that’s a resistance. Once a resistance is broken (price 
goes above it), it can become support (a concept called “role reversal” or support-turned-resistance 
and vice versa). 
• 

Multiple Timeframe S/R: Often weekly or monthly chart levels are more significant than 

daily levels. A weekly support might be a zone where price reversed over a multi-week downturn. In 
practice, one might mark those and then look at daily for finer levels. 

• 

Psychological levels: Round numbers (like $100, $50) often act as S/R simply because 

many orders cluster there. Not a rule, but noticeable sometimes. 

• 

For our workflow, since we’re computing from price data, a simple approach: look at the 
recent highest high and lowest low. For example, over the last 60 days, what’s the max and min close 
(or high) price? Those could be considered current resistance and support levels. Another approach is to 
find local peaks/troughs (like find days where price is higher than some days before and after – a local 
maximum). Those local extrema can be potential S/R points. 

• 

Institutional usage: Institutions often combine S/R with volume (volume by price, 

showing at what prices a lot of shares traded – those often become S/R). We won’t do volume-by-price 
analysis here, but volume at certain price levels is an advanced confirmation of S/R. 

• 

S/R also feeds into strategies: e.g., if price breaks above a known resistance, that often 

triggers buy signals (breakout strategy) especially if on high volume. Or if price falls below support, a 
wave of selling might happen (stop losses hit). So knowing these levels helps understand the signals we 
generate – a buy signal near support is safer; a sell signal right above a support might have limited 
downside (maybe not far to go since support could catch it). 
Common Pitfalls & Best Practices: 

• 

Not exact points: Support and resistance are usually zones, not precise lines. Price 

might overshoot a bit (false breakout) and then revert. So be careful treating them as binary. In coding, we 
might identify a level, but in usage, allow some tolerance. For instance, if we say resistance ~ $100, price 
might poke to $102 and then drop – it doesn’t mean our level was “wrong,” it’s a zone around $100. We 
can’t easily handle “zones” in code except by perhaps marking a range (like support ±2%). For simplicity, 
we’ll just mark levels and keep this concept in mind. 

• 

Too many levels: Every small swing high/low can be considered a minor S/R. Focus on 

more significant ones (e.g., 2-month high/low, or multi-bounce levels). We’ll likely restrict to something like 
the highest high and lowest low of the last N days (which is straightforward). That gives a broad picture. 
Dynamic shifting: When a new high is made, resistance moves up; old resistance may 

• 

become support. Our calculation should update if new extremes are set. 

• 

Ignoring trend: A support in a downtrend will eventually break, and a resistance in an 

uptrend eventually breaks; don’t treat them as unbreakable. Instead, understand trend context (which we 
have via MAs, etc.). For example, shorting at a resistance when all trend indicators are bullish and 
volume is high might be fighting the trend – risky. It might be better to wait for confirmation of a reversal at 
resistance. We incorporate trend indicators to avoid counter-trend signals solely due to S/R. 
n8n Node Configuration: 
Add a Function node “Calc SupportResistance” after Volume. We’ll implement a simple version: 

• 

Look back a certain window (e.g., 60 days) from the last day, or simply use full data: find 

the maximum high price and minimum low price in that window. Those can be considered current major 
resistance and support. Alternatively, could use Close prices rather than High/Low. Using High for 

 
 
 
 
 
 
 
 
 
 
 
resistance and Low for support is logical (since intraday peaks/troughs matter). If the sheet doesn’t have 
separate High/Low columns (but our OHLCV implies we do have High and Low), use them. 

• 

We might also derive a second level, like second highest high (to have a notion of next 

resistance above, but let’s keep it simple). 

• 

Actually, a 60-day high is basically a 2-month resistance (if current price is below it), or if 
current price is at all-time high, the 60-day high is current price and there’s no resistance above (we could 
mark none or consider that level as support after breakout). 

• 

Let’s do: for the most recent data point (last item in array), find past 60-day min and max. 

Add fields SupportLevel and ResistanceLevel to that last item (and possibly to all items, though 
historically it’s tricky to have a “current” S/R for each date without a complex algorithm). Actually, maybe 
we want to output S/R for each day as what the support/resistance was at that time (like a rolling 
calculation)? That’s complex for resistance (you’d need to know future to know a peak was a peak). 
Instead, it might be enough to output current levels for the latest data. Since the final result in Google 
Sheets likely will be the latest signals, we could store the S/R levels alongside the latest signal. If doing 
backtesting row-by-row, one might compute S/R dynamically up to that day (which is possible: for each 
day, look at previous 60 days to define that day’s known S/R). That’s more proper if we were simulating 
being “in the moment” each day. Let’s do that: for each item (day), find the highest High of the previous 60 
days (including that day perhaps for resistance?) and lowest Low of previous 60 days. However, taking 
previous 60 including current will just yield current high as resistance on that day which is trivial. Perhaps: 

point. 

• 

• 

Resistance on day i = max(High[j] for j from i-59 to i) – basically 60-day high up to that 

Support on day i = min(Low[j] for j from i-59 to i) – 60-day low. 

This means on any given day, we look back 60 days. If today’s price is at the resistance level it means it’s 
a 60-day high. If it’s at support level, 60-day low. This is a simplistic approach to gauge relative position. 
Traders often use 50-day high/low as breakout points as well. 

• 

Alternatively, use a longer period like 250 days (1 year) to mark truly major S/R – but then 

short-term signals might ignore intermediate levels. 60 is a compromise. 
We’ll implement for each day for completeness so we can use it in backtest analysis too. 
Add fields: Resist60 and Support60. These are the 60-day lookback high and low respectively for each 
date. (For first 59 days, they’ll be based on whatever data available – we might start from day 1 using all 
up to that day, that’s fine.) 
Full JavaScript Code (Function node: Calc SupportResistance): 
const inputItems = items; 
if (inputItems.length === 0) { 
  return []; 
} 
const lookback = 60; 
for (let i = 0; i < inputItems.length; i++) { 
  const startIdx = i - lookback + 1; 
  const fromIdx = startIdx < 0 ? 0 : startIdx; 
  let maxHigh = -Infinity; 
  let minLow = Infinity; 
  for (let j = fromIdx; j <= i; j++) { 
    const high = parseFloat(inputItems[j].json.High); 
    const low = parseFloat(inputItems[j].json.Low); 
    if (high > maxHigh) maxHigh = high; 
    if (low < minLow) minLow = low; 
  } 
  inputItems[i].json.Resist60 = maxHigh === -Infinity ? null : parseFloat(maxHigh.toFixed(2)); 

 
 
 
 
 
 
  inputItems[i].json.Support60 = minLow === Infinity ? null : parseFloat(minLow.toFixed(2)); 
} 
return inputItems; 
Explanation: For each day i, we scan back up to 59 days before it (or from day 0 to i if i < 60) to find 
highest High and lowest Low. That’s our rolling 60-day resistance and support. We add those values. On 
the last day, Resist60 is the highest high of last 60 days (which might be that day’s high if it’s a new high, 
or an earlier one otherwise), and Support60 is the lowest low of last 60 days. 
Usage: If today’s Close is near Resist60 and our other indicators show bullish, a breakout might be 
happening. If today’s Close is still far from Resist60 (below it), that Resist60 is a potential target or 
obstacle. If today’s Close is above the Resist60 value (meaning today made a new high), that level might 
have been broken – often a bullish sign especially if volume confirms. Similarly for support. 
This is a basic measure. In signals, we might use it qualitatively: e.g., if price is making a 60-day high 
(Close == Resist60 today) on strong indicators, that’s a bullish breakout – possibly a strong buy signal. If 
price is at a 60-day low (Close == Support60) and indicators align bullish (oversold etc.), maybe a 
mean-reversion buy. Or if price breaks below support with bearish indicators, that’s a sell. 
2.7 Advanced Oscillators: Stochastic Oscillator (14, 3) and Average True Range (ATR, 14) 
Finally, we cover two additional indicators: Stochastic Oscillator and ATR. These are somewhat optional 
in a basic strategy, but the prompt asks for them, and they provide further insight: 

• 

Stochastic Oscillator: Another momentum indicator that compares the current price to 
the range over a recent period (often 14 days). It outputs two lines %K and %D. %K is basically (Close - 
LowestLow14) / (HighestHigh14 - LowestLow14) * 100. %D is a 3-day SMA of %K (a smoother line). 
Stochastic values range 0 to 100. Interpretation is similar to RSI: above 80 = overbought, below 20 = 
oversold. Signals often come when %K crosses %D (like mini MACD) – e.g., %K crossing below %D in 
overbought zone is a sell, crossing above %D in oversold zone is a buy. Stochastic can sometimes give 
earlier signals than RSI because of the %D trigger. It’s useful in oscillating markets and even in trends to 
spot pullback exhaustion. However, it too can stick in overbought during strong trends. Professionals 
might use stochastic mainly for shorter-term timing in a trading range or to confirm RSI signals. We will 
calculate %K and %D for 14 period %K and 3 period %D. 

• 

Average True Range (ATR): A volatility indicator measuring the average range of price 

movement in a period (typically 14 days). True Range (TR) is defined as the maximum of: high-low, |high - 
prevClose|, |low - prevClose| (this accounts for gaps). ATR is the 14-day average of TR (Wilder’s 
smoothing often). ATR doesn’t give directional signals, but tells you how volatile the asset is. Traders use 
ATR for setting stop-loss distances (e.g., a stop may be placed 1.5*ATR below entry to account for normal 
volatility). Also, a suddenly rising ATR can indicate a breakout or trend acceleration (volatility increasing). 
A falling ATR indicates a quieting market. We can include ATR to gauge volatility regime or incorporate it 
into signal strength (for instance, if ATR is extremely low, maybe weight breakouts more, or if extremely 
high, caution as market is wild). For our algorithm, we might not use ATR in the multi-indicator conditions 
explicitly, but we will calculate it because it’s requested and it’s useful to see. Perhaps we could use ATR 
change as part of volume/volatility confirmation: e.g., if ATR is rising along with a breakout, that confirms 
a regime change to higher volatility, which often accompanies breakouts. 
Common Pitfalls: 
• 

Stochastic can give a lot of false signals if used alone. It’s very jumpy. Best to use it in 

conjunction: e.g., ensure trend is flat if you want to use overbought/oversold swing trades, or only take its 
signals in direction of larger trend. 

• 

ATR is not a directional indicator, so don’t attempt to interpret high ATR as bullish or 

bearish – it just means big moves (could be big up or big down). Some might confuse ATR increase with 
impending reversals (not necessarily; ATR can rise in a crash and then drop when the market calms at 
bottom – ATR just measures range). Use it for risk management or understanding if market is in a quiet or 
volatile state. 

 
 
 
 
n8n Node Configuration: 
Add a Function node “Calc Stoch & ATR” after SupportResistance. 
For Stochastic (14,3): We need for each day from day 13 onwards: 

• 
• 

lowest low of last 14 days (including current), highest high of last 14 days. 
%K = (Close_today - lowestLow14) / (highestHigh14 - lowestLow14) * 100. (If 

highestHigh == lowestLow, then %K is 0 or 100? Actually if high==low, means no movement, we can set 
%K = 0 or 100 both would be kind of arbitrary; but that scenario is basically no volatility, so any close is 
both highest and lowest. We can define %K=0 in that degenerate case or just 0 as default). 

• 

%D = 3-day SMA of %K (we can calculate on the fly as well). 

For ATR (14): 

• 

Compute True Range (TR) for each day: TR = max( High_today - Low_today, 

|High_today - Close_yesterday|, |Low_today - Close_yesterday| ). For day 0, TR can be just High0-Low0 
(no prev close). 
• 

Then ATR14 = Wilder’s smoothing of TR or simple 14 SMA of TR. We can do Wilder like 

we did for RSI average losses: 

• 
• 

First ATR value at day 13 = average of TR0..TR13. 
Thereafter ATR = (prevATR * 13 + currentTR) / 14. 

This yields a nice smoothing. Or we can just do simple moving average to simplify code. Wilder’s is 
standard though. We’ll implement Wilder’s to be consistent with typical ATR. 
Add fields: StochK, StochD, ATR. Possibly scale ATR to same units as price (it will be in price units, e.g., 
if stock is $100 and ATR 5 means a $5 average range). We can leave as is. 
Full JavaScript Code (Function node: Calc Stoch & ATR): 
const inputItems = items; 
if (inputItems.length === 0) { 
  return []; 
} 
// Prepare arrays for stoch %K and %D 
const stochK = []; 
const stochD = []; 
// Prepare for ATR 
const TR = []; 
const ATR = []; 
const period = 14; 
// Calculate True Range for each day 
for (let i = 0; i < inputItems.length; i++) { 
  const high = parseFloat(inputItems[i].json.High); 
  const low = parseFloat(inputItems[i].json.Low); 
  let tr; 
  if (i === 0) { 
    tr = high - low; 
  } else { 
    const prevClose = parseFloat(inputItems[i-1].json.Close); 
    const range1 = high - low; 
    const range2 = Math.abs(high - prevClose); 
    const range3 = Math.abs(low - prevClose); 
    tr = Math.max(range1, range2, range3); 
  } 
  TR.push(tr); 
} 

 
 
 
 
 
 
 
// Compute ATR using Wilder's smoothing 
let sumTR = 0; 
for (let i = 0; i < TR.length; i++) { 
  if (i < period) { 
    sumTR += TR[i]; 
    if (i === period - 1) { 
      // first ATR (at index 13) = avg of TR0-13 
      const firstATR = sumTR / period; 
      ATR.push(parseFloat(firstATR.toFixed(4))); 
    } else { 
      ATR.push(null); 
    } 
  } else { 
    // subsequent ATR 
    const prevATR = ATR[i-1]; 
    const newATR = ((prevATR * (period - 1)) + TR[i]) / period; 
    ATR.push(parseFloat(newATR.toFixed(4))); 
  } 
} 
// Calculate Stochastic %K and %D 
for (let i = 0; i < inputItems.length; i++) { 
  if (i < period - 1) {  
    stochK.push(null); 
    stochD.push(null); 
  } else { 
    // find highest high and lowest low of last 14 days (including today) 
    let highestHigh = -Infinity; 
    let lowestLow = Infinity; 
    for (let j = i - (period - 1); j <= i; j++) { 
      const hj = parseFloat(inputItems[j].json.High); 
      const lj = parseFloat(inputItems[j].json.Low); 
      if (hj > highestHigh) highestHigh = hj; 
      if (lj < lowestLow) lowestLow = lj; 
    } 
    const close = parseFloat(inputItems[i].json.Close); 
    const denom = (highestHigh - lowestLow); 
    let k; 
    if (denom === 0) { 
      k = 50; // if no range, set %K to 50 (neutral) as a fallback 
    } else { 
      k = ((close - lowestLow) / denom) * 100; 
    } 
    stochK.push(k); 
    // Now %D = SMA of last 3 %K values (or fewer if at start) 
    if (i < period + 1) { 
      // first two D values can't be full SMA3 if not enough, we can set D equal to K or null 
      stochD.push(null); 
    } else { 
      const K1 = stochK[i];     // K today 

      const K2 = stochK[i-1];   // K yesterday 
      const K3 = stochK[i-2];   // K day before 
      const d = (K1 + K2 + K3) / 3; 
      stochD.push(d); 
    } 
  } 
} 
// Attach to items 
return inputItems.map((item, idx) => { 
  item.json.ATR14 = ATR[idx]; 
  item.json.StochK = stochK[idx] !== null ? parseFloat(stochK[idx].toFixed(2)) : null; 
  item.json.StochD = stochD[idx] !== null ? parseFloat(stochD[idx].toFixed(2)) : null; 
  return item; 
}); 
Explanation: We compute TR for each day accounting for gaps. Then ATR using smoothing (Wilder). For 
Stoch %K, for each day from 13 onward, find last 14 days high/low. Compute %K. If high == low (no price 
movement over 14 days, very unusual but possible in some flatlined scenario), we set %K = 50 (midpoint) 
as a sensible default (the code uses 50). Then for %D, we need the 3-day average of %K. We did a 
simple approach: we only compute D when we have 3 K values (so effectively from day 15 onward). For 
day 14, we push D as null or we could just copy K for first instance, but not needed. After that, it averages 
the last 3 K’s. 
We round StochK and StochD to 2 decimals to be neat. ATR to 4 decimals. 
Now the data is enriched with all requested indicators: 

• 
• 
• 
• 
• 

Trend: SMA20,50,200; EMA20,50,200 
Momentum: RSI14; StochK, StochD; MACD, MACD_Signal, MACD_Hist 
Volatility: BB_upper, BB_mid, BB_lower, BB_width; ATR14 
Volume: Volume itself, VolAvg20, VolRatio, VolSpike 
Support/Resistance: Support60, Resist60 

It’s a lot of information! This is akin to what an analyst would have on their chart to make a decision. Next, 
we need to synthesize this into actual trading signals. 
Step 3: Generating Trading Signals (Multi-Indicator Strategy) 
This is the critical step where we combine all the technical indicator inputs to produce actionable Buy/Sell 
signals. The aim is to use multiple confirmations so that the signals are “professional-grade” with fewer 
false positives. We’ll also incorporate volume confirmation, and provide a signal strength metric that 
reflects how many indicators agree on the signal. 
We should design a clear set of rules. An example approach for a bullish (Buy) signal might be: 

• 

Trend Alignment: Price above a certain MA threshold or a bullish MA crossover (e.g., 

price > SMA50 and SMA50 > SMA200 suggests uptrend), OR maybe MACD above zero (positive 
momentum) as a trend filter. 

• 

Momentum Trigger: RSI crossing above a threshold (coming out of oversold) , or Stoch 

crossing up from oversold, or MACD line crossing above signal line. These indicate the timing of a 
potential upward move. 

• 

Support Level Proximity: It could be a stronger signal if it occurs near a known support 

(meaning limited downside). For instance, price bounced from near Support60, giving confidence the 
support held. Not a must, but adds weight. 

• 

Volume Confirmation: Ideally, the up move is accompanied by above-average volume 

(VolSpike true or VolRatio > 1). If volume is low, perhaps don’t trigger a buy unless other indicators are 
extremely strong. 

 
 
 
 
 
 
 
 
 
• 

Volatility Consideration: If Bollinger Bands were tight and now price breaks above the 
upper band, that’s a strong breakout sign (especially with volume). Or if ATR was low and starts rising, it 
indicates regime change to higher volatility which often means a trending move starting. 
For a bearish (Sell) signal, roughly the opposite: 

• 
• 

Trend down (price < SMA50 and SMA50 < SMA200, for example), or MACD below zero. 
Momentum: RSI dropping from above, or Stoch crossing down from overbought, or 

MACD cross down. 

• 
• 

Resistance: maybe near a resistance level (price failed near Resist60). 
Volume: heavy volume on the drop (or low volume on the last push up which failed, 

showing lack of demand). 

• 

Volatility: maybe bands were tight and now breaking down or ATR rising. 

We also might generate a “neutral” or no-trade signal if conditions are mixed. 
Configurable Signal Strength: We will implement a scoring system. For example: 

• 

We list a bunch of conditions (bullish conditions and bearish conditions). Each condition 

met adds +1 to a bullish score or +1 to a bearish score. 

• 

Some conditions could be worth more weight (maybe give trend alignment 2 points since 

trading with the trend is important). But initially, we can keep it equal for simplicity. 

• 

After evaluating, if bullish score is high and bearish is low, that’s a buy signal. If bearish 

score is high and bullish low, sell signal. If both are low or somewhat balanced, no strong signal. 

• 

The signal strength metric can be the difference or the absolute sum of whichever side. 

Or simply the max of the two. We can also present the number of conditions confirmed. The user can 
decide what threshold = actionable. For instance, require at least 3 bullish conditions to call it a “Buy”. 
We’ll allow configuration by making the conditions clear in code (so one can tweak thresholds easily if 
needed). 
Let’s define conditions: 
(We should base on the outputs we have. Also, ensure we’re using them logically – e.g., we should avoid 
contradictory conditions double counting. Also, we should only generate one signal per day ideally – 
either buy, sell, or none. We could also output “Hold” or “No signal” for clarity.) 
Bullish conditions (examples): 

• 

Trend: Close > SMA50 and SMA50 > SMA200. This indicates short and long MAs 

aligned up (price in uptrend) – a strong bullish context. We can give +1 for this alignment. 

• 

Or simpler trend: Close > SMA200 (above long-term average) could be one condition, 

and maybe Close > SMA50 as another (above intermediate average). 

• 

MACD: MACD > MACD_Signal (MACD line crossed above signal line) – momentum 

turning up. +1. And maybe MACD > 0 (above zero line) as a separate condition (meaning momentum is 
overall bullish). That could be another +1. 

• 

RSI: RSI14 > 50 could indicate momentum in bullish half. Or specifically, if yesterday RSI 

< 30 and today RSI > 30 (just crossed up out of oversold), that’s a strong buy trigger. We might not track 
yesterday in final output easily unless we iterate. Actually, since we have all days, we can check the 
previous item’s RSI. Yes, in code we can reference previous index. Let’s define: if RSI today > 30 and RSI 
yesterday <= 30, add +1 (oversold bounce signal). Also, if RSI is just generally > 50 (bullish momentum), 
+1 (but that condition might be always true in an uptrend, which is fine, it just adds weight). If RSI > 70, 
actually that’s overbought so not bullish – that might even be a bearish condition if we want to add. 
Possibly we add a bearish condition for RSI > 70 (overbought). Similarly bullish condition for RSI < 30 
(oversold) might be contrarian buy, but more precisely, crossing out of oversold is the actionable part. 
We’ll implement crossing signals more than static levels to avoid staying in oversold. 

• 

Stochastic: If StochK and StochD are below 20 and StochK crosses above StochD, that’s 

a classic buy. We can approximate: if StochK today > StochD today and StochK yesterday <= StochD 
yesterday and StochD yesterday < 20 (so they were in oversold zone), then +1. Or simpler: if StochK < 20 

 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
(oversold) add +1 (momentum ripe to reverse), and if today StochK > yesterday StochK (momentum 
turning up) add another. We have many possibilities, but let’s not overweight it – maybe just include one 
stoch condition like “oversold and turning up”. 

• 

Bollinger: If Close yesterday was below lower band and today’s close is back above lower 
band (meaning it reverted from an oversold extreme), that could be a bullish mean reversion sign. Also, if 
bands were narrow (BB_width low) and now price breaks above the upper band, that’s a bullish breakout 
sign. For breakout: if today’s Close > today’s BB_upper and BB_width is in lowest quartile of last 60 days 
(we can derive a threshold for width). Simpler: if VolSpike is true and Close > BB_upper, likely a breakout 
with volume -> strong buy. Or we can just fold that into a general observation that if price is at 60-day high 
(Resist60 broken) and volume spike, we have that anyway. 

• 

Support: If Close is very near Support60 and we get a bounce (like yesterday was the 

lowest low, today up), then that’s a bounce off support. We can say if Close today > Close yesterday and 
yesterday’s Low was equal to Support60 (hit 60-day low), that’s a bullish bounce off support. 
Volume: If VolSpike is true and price is up (Close > prev Close), that’s bullish 

• 

confirmation. +1. If volume is low (VolRatio < 0.5) on a supposed breakout, we might not count the signal 
at all or reduce. We can incorporate that by giving a bearish or “anti-confirmation” condition for very low 
volume on a breakout scenario. 

• 

Others: If ATR has been rising or BB_width expanding along with an upward move, it 
confirms volatility expansion in direction of trend – not explicitly needed to code, might reflect in others 
already. 
Bearish conditions: similarly inverse: 

• 

Trend: Close < SMA50 and SMA50 < SMA200 (downtrend). Or Close < SMA200 as one, 

Close < SMA50 as another. 

• 
• 

MACD: MACD < MACD_Signal (bearish cross), and MACD < 0. 
RSI: crossing below 70 from above as a sell trigger, or simply RSI < 50 (momentum 

bearish). If yesterday RSI >= 70 and today RSI < 70, that’s a potential sell (overbought turning down). Or 
if RSI is above 70, that by itself could warn of overbought (though in strong trends it stays high, so best to 
use the cross). 
• 
• 

Stoch: if K crosses below D from above in overbought zone (>80). 
Bollinger: price closed back inside after poking above upper band could be a short signal 

(if other indicators confirm). Or price breaking below lower band on volume (breakdown). 

• 

Resistance: if price hit Resist60 and can’t go above, and then turns down, that’s bearish. 

e.g., if today’s High was Resist60 and it closed lower or red candle, plus indicators turn down, that’s a 
potential sell. 

• 

Volume: If a down move happens on high volume, it confirms selling pressure (bearish). 
Also if a rally happens on very low volume (no buyers), it could be a false rally – maybe a bearish sign to 
fade the rally, but that’s more subjective. We might skip that nuance. 
Given the complexity, we won’t implement every one of these, but a reasonable subset to capture the 
essence: 
Let’s choose a set for code: 
Bullish (+1 each): 
• 

Close > SMA50 and SMA50 > SMA200 (trend up confirmation) – we ensure both with 

one condition for a strong uptrend alignment. 

• 

MACD > MACD_Signal (recent bullish crossover) and maybe MACD_Hist turned positive 

(we could combine that as effectively the same, MACD > Signal means hist > 0). So just one condition 
here. 

• 

RSI14 crossing up from <=30 to >30 (oversold bounce) – means yesterday RSI <=30, 

today >30. 

 
 
 
 
 
 
 
 
 
 
 
 
 
 
• 

If not oversold scenario, then maybe RSI > 50 as general momentum. (But careful: if it 

just crossed 50 from below that’s bullish, if it’s always >50, it’s just trend context – but it’s fine to count it.) 
StochK cross above StochD in oversold zone: we can implement as: if StochD yesterday 

• 

< 20 and StochK today > StochD today. 

• 

Close broke above Resist60 (meaning yesterday Close <= Resist60 and today Close > 

Resist60) – breakout to new 60-day high. That’s strong bullish. 

• 

VolSpike on a up day (Close > prev Close) – volume confirmation. If today’s close > 

yesterday’s close and VolSpike true, +1. 
Bearish (+1 each): 

• 
• 
• 

• 
• 

<70. 

overbought). 

Close < SMA50 and SMA50 < SMA200 (downtrend alignment). 
MACD < MACD_Signal (bearish cross). 
RSI14 crossing down from >=70 to <70 (overbought drop) – yesterday RSI >=70, today 

RSI14 < 50 as general momentum bearish. 
StochD yesterday > 80 and StochK today < StochD today (stochastic cross down from 

• 

Close broke below Support60 (yesterday Close >= Support60, today Close < Support60) 

– breakdown to new low. 

• 

VolSpike on a down day (heavy selling). If today’s close < yesterday’s and VolSpike true, 

+1. 
We should also consider adding a mild condition if price is just below a resistance (like close to Resist60) 
as bearish bias (because it might fail there), or just above support as bullish bias. But those are weaker 
signals unless accompanied by actual bounce or break. We handled bounce/break with crossing 
conditions above. 
Combine and Decide: 
After adding scores, we decide: 

• 
• 
• 

If bullish_score >= some threshold and bullish_score > bearish_score: signal = “Buy”. 
If bearish_score >= some threshold and bearish_score > bullish_score: signal = “Sell”. 
If neither dominates or scores are low: signal = “Hold” or no trade. 

We can set threshold = 2 or 3 so that at least a couple of conditions align. If only 1 condition triggered, 
might be noise. 
We’ll also compute a SignalStrength perhaps as the difference (bullish_score - bearish_score) or just the 
count of whichever signal. We might present it as an absolute number with sign: e.g., +3 means strong 
buy, -2 means moderate sell, 0 means no bias. 
Given we’ll likely produce one row of output (for latest date) at the end to store, we might compute signal 
only for the last item. But since we support backtesting, we can compute it for each day historically as well 
– this means the algorithm triggers signals as if it was running on each day in history. This is good for 
testing – you can see how many signals it would have given. 
So we can do it for each item (except maybe the very first few that lack data). 
n8n Node Configuration: 
Add a Function node “Generate Signals” after the last indicator node. It will loop through each item (each 
day’s data) and compute bullish_score, bearish_score based on previous nodes’ output fields, possibly 
referencing the previous day’s values for cross signals. 
Full JavaScript Code (Function node: Generate Signals): 
const inputItems = items; 
if (inputItems.length === 0) { 
  return []; 
} 
const outputItems = inputItems.map((item, idx) => { 

 
 
 
 
 
 
 
 
 
 
 
 
 
 
  const data = item.json; 
  let bull = 0; 
  let bear = 0; 
  const prevData = idx > 0 ? inputItems[idx-1].json : null; 

  // 1. Trend conditions 
  if (data.SMA50 !== null && data.SMA200 !== null) { 
    if (data.Close > data.SMA50 && data.SMA50 > data.SMA200) { 
      bull += 1; 
    } 
    if (data.Close < data.SMA50 && data.SMA50 < data.SMA200) { 
      bear += 1; 
    } 
  } 

  // 2. MACD cross 
  if (data.MACD !== undefined && data.MACD_Signal !== undefined) { 
    if (data.MACD > data.MACD_Signal) { 
      bull += 1; 
    } 
    if (data.MACD < data.MACD_Signal) { 
      bear += 1; 
    } 
  } 

  // 3. MACD above/below zero (extra weight) 
  if (data.MACD !== undefined) { 
    if (data.MACD > 0) bull += 1; 
    if (data.MACD < 0) bear += 1; 
  } 

  // 4. RSI crossing out of overbought/oversold 
  if (data.RSI14 !== undefined && prevData) { 
    if (prevData.RSI14 !== null && prevData.RSI14 <= 30 && data.RSI14 > 30) { 
      // oversold -> above 30 
      bull += 1; 
    } 
    if (prevData.RSI14 !== null && prevData.RSI14 >= 70 && data.RSI14 < 70) { 
      // overbought -> below 70 
      bear += 1; 
    } 
  } 
  // General RSI trend 
  if (data.RSI14 !== null) { 
    if (data.RSI14 > 50) bull += 1; 
    if (data.RSI14 < 50) bear += 1; 
  } 

  // 5. Stochastic cross in extreme zones 

   
   
   
   
   
  if (data.StochK !== null && data.StochD !== null && prevData && prevData.StochK !== null && 
prevData.StochD !== null) { 
    // bullish stochastic: was oversold and K crossed above D 
    if (prevData.StochD < 20 && data.StochK > data.StochD && prevData.StochK <= prevData.StochD) { 
      bull += 1; 
    } 
    // bearish stochastic: was overbought and K crossed below D 
    if (prevData.StochD > 80 && data.StochK < data.StochD && prevData.StochK >= prevData.StochD) { 
      bear += 1; 
    } 
  } 

  // 6. Support/Resistance break 
  if (data.Resist60 !== null && prevData) { 
    // bullish breakout above resistance 
    if (prevData.Close <= prevData.Resist60 && data.Close > data.Resist60) { 
      bull += 1; 
    } 
    // bearish breakdown below support 
    if (prevData.Close >= prevData.Support60 && data.Close < data.Support60) { 
      bear += 1; 
    } 
  } 

  // 7. Volume confirmation 
  if (data.VolSpike !== undefined && prevData) { 
    if (data.VolSpike && data.Close > prevData.Close) { 
      bull += 1; 
    } 
    if (data.VolSpike && data.Close < prevData.Close) { 
      bear += 1; 
    } 
  } 

  // 8. Additional volume logic: if volume is extremely low on a supposed breakout, reduce score (e.g., if 
price > Resist60 but VolRatio < 0.5, maybe discount it) 
  if (data.Resist60 !== null && prevData) { 
    if (prevData.Close <= prevData.Resist60 && data.Close > data.Resist60 && data.VolRatio !== null && 
data.VolRatio < 0.5) { 
      // breakout happened but volume was <50% avg -> likely false breakout 
      bull -= 1; // negate one bullish point if any 
    } 
    if (prevData.Close >= prevData.Support60 && data.Close < data.Support60 && data.VolRatio !== null 
&& data.VolRatio < 0.5) { 
      // breakdown but low volume -> false breakdown 
      bear -= 1; 
    } 
  } 

   
   
   
   
  // Ensure scores are not negative from adjustments 
  if (bull < 0) bull = 0; 
  if (bear < 0) bear = 0; 

  // Determine signal 
  let signal = "Hold"; 
  let strength = 0; 
  if (bull >= 2 && bull > bear) { 
    signal = "Buy"; 
    strength = bull; 
  } else if (bear >= 2 && bear > bull) { 
    signal = "Sell"; 
    strength = bear; 
  } else { 
    signal = "Hold"; 
    strength = bull >= bear ? bull : -bear; // if no clear winner, give signed strength or 0 
  } 

  // Attach signal info 
  item.json.Signal = signal; 
  item.json.SignalScoreBull = bull; 
  item.json.SignalScoreBear = bear; 
  item.json.SignalStrength = strength; 
  return item; 
}); 
return outputItems; 
Explanation: This code evaluates each day (each item in data) against the conditions described: 

• 

Trend alignment: bull++ if uptrend, bear++ if downtrend (we check both Close vs SMA50 
and SMA50 vs SMA200) – if both are true, bull gets 1. If both are false but downtrend true, bear gets 1. If 
mixed, none. 

• 
• 
• 
• 
• 

MACD cross: straightforward. 
MACD sign: giving another point in direction of MACD above/below zero. 
RSI crosses out of extremes: uses prev day data. Only count when crossing threshold. 
RSI midline: above/below 50. 
Stoch cross: We look at yesterday K vs D and D in extreme, and today’s cross. This 

ensures we only count at the moment of crossing after an extreme. 

• 

Support/res breakouts: compares yesterday’s close relative to yesterday’s resist/support, 
and today’s close relative to today’s resist/support (which might be same or updated but similar concept). 
Essentially if today made a new 60-day high, bull++, if new 60-day low, bear++. 

• 

Volume spikes: if volume spike and price moved up from yesterday, bull++ (strong buying 

volume); if volume spike and price moved down, bear++. 

• 

Additional volume adjustment: If a breakout above resistance happened without volume 

(VolRatio < 0.5), we subtract a bull point (it might have added one in Resist60 check, so we cancel it). 
Similarly for breakdown without volume. This prevents a low-volume breakout from incorrectly signaling 
strong buy. 

• 
addition). 
• 

Then we ensure bull/bear aren’t negative (just in case we subtracted without initial 

Decide signal: require at least 2 bullish signals and bull > bear to call a Buy. Similarly for 

Sell. If not, signal Hold. The strength we output: if Buy, we output number of bullish conditions (bull). If 

   
   
 
 
 
 
 
 
 
 
 
 
 
Sell, we output negative of bear or bear (we could make strength negative to indicate sell, but we also 
have Signal field, so maybe keep strength positive magnitude for strength). Alternatively, define strength 
as bull (if buy) or -bear (if sell) to indicate direction in one number. Above, I did strength = bull for buy, 
strength = bear for sell, but that doesn’t differentiate buy vs sell. Perhaps better: for hold or uncertain, 
make it 0 or small. But the user asked for a “signal strength metric”. We can output bull and bear 
separately anyway. Or output SignalStrength as positive for buy and negative for sell. I partly did strength 
= bull or bear, which loses sign info, but then in else I tried something: strength = bull >= bear ? bull : 
-bear;. That would give a signed number in hold case. But for consistency, maybe we should do: 

• 
• 
• 

If signal is “Buy”: SignalStrength = bull (e.g., 3 meaning 3 bullish criteria). 
If “Sell”: SignalStrength = -bear (e.g., -2 meaning 2 bearish criteria). 
If hold: could give difference or 0. But to keep it simple: we can set 0 for Hold. Or if we 

want them to see lean, we could output e.g. +1 or -1 if one side had a slight edge but not enough 
threshold. This code in else did that (taking bull or -bear whichever bigger). That might confuse though. 
Possibly better to just output 0 on holds and the separate scores if they want detail. 
Given they specifically mention a “signal strength metric”, I’d interpret that as an absolute measure of 
confidence either way. So maybe output +N for buy strength, -N for sell strength, 0 for none. I’ll implement 
that: If signal is Buy, strength = bull (positive). If Sell, strength = -bear. If Hold, strength = 0 (or could use 
bull - bear to indicate bias, but let’s keep it simple: no signal means 0 strength). 
I’ll adjust that after computing bull, bear: 
  let signal = "Hold"; 
  let strengthMetric = 0; 
  if (bull >= 2 && bull > bear) { 
    signal = "Buy"; 
    strengthMetric = bull;    // positive indicating buy strength 
  } else if (bear >= 2 && bear > bull) { 
    signal = "Sell"; 
    strengthMetric = -bear;   // negative indicating sell strength 
  } else { 
    signal = "Hold"; 
    strengthMetric = 0; 
  } 
  item.json.Signal = signal; 
  item.json.SignalStrength = strengthMetric; 
  item.json.BullScore = bull; 
  item.json.BearScore = bear; 
Now each item has a Signal (Buy/Sell/Hold) and a strength. 
Volume-based confirmation is built in via the VolSpike conditions and the adjustment for low volume 
breakouts. This addresses the requirement to use volume to reduce false signals. 
We also made things configurable implicitly – one can adjust thresholds (like require 3 conditions instead 
of 2 by changing the if check from >=2 to >=3). One could also weight differently by adding 2 instead of 1 
somewhere. This can be done in code. 
At this point, the data for each day includes what the trading signal would be on that day given the info up 
to that day (we didn’t use future data aside from including that day’s values – which is fine because a 
signal on that day would be at close of that day typically after seeing indicators of that day). 
Important: Our signals likely refer to end-of-day signals to act on next day’s open (common in EOD 
strategies). That’s fine; backtesting one could simulate buying next day if a Buy appears. 
We should ensure to mention that if using daily bars, signals come at the close of the day when 
conditions met, and you’d trade next day open (in practice). 
Now we have the signals. Let’s proceed to store results. 

 
 
 
Step 4: Storing Results Back in Google Sheets 
We want to write our analysis results (indicators and signals) to Google Sheets so they are saved and 
easy to view. There are a few ways to structure this: 

• 

Option 1: Write the full historical data with all new columns back to a sheet (basically 

augmenting the original data). For example, you had a sheet with Date, OHLCV; you could add columns 
for each indicator (SMA20, RSI14, etc.) and the signal. This way everything is in one sheet per ticker. This 
could be a lot of columns (we calculated many indicators!). You might choose to only output key ones or 
the final signals to avoid clutter. 

• 

Option 2: Write only the latest signal (or a summary) to a separate sheet, effectively 

logging the signals. For example, a sheet with columns: Date, Ticker, Signal, Strength, maybe some key 
indicator values. Each run of the workflow would append the latest day’s signal. This is more of a log of 
recommendations. 
• 

Option 3: Two-tier approach: one sheet per ticker with detailed data (for backtesting and 

reference), and one consolidated “alerts” sheet for most recent signals of all tickers. 
The prompt suggests including “Technical indicator values, Final buy/sell signals, Signal strength metric” 
in the sheet. It doesn’t explicitly say whether to store historical or just final, but likely they want to see all 
results, perhaps per date. We should lean towards writing the output for each date (which supports 
backtesting as well). So we will effectively update the original data rows with new columns for indicators 
and signals. 
Google Sheets Append/Update Setup: 
We will use the Google Sheets node in “Append or Update” mode. This mode needs a unique key to 
match rows. The best key is the Date (assuming each date appears once per ticker). We will configure: 

• 
• 

Resource: “Sheet” (within a spreadsheet). 
Operation: Append or Update Row. This will attempt to find a row with the matching 

key and update it, otherwise append a new row at bottom . 

• 

Document: select your spreadsheet. Could be the same as input or a different one. 

Often, we use the same for simplicity (so the data and results are side by side). 

• 

Sheet: select the specific sheet (ticker sheet). If inside a loop, use the ticker variable for 

sheet name as we did for reading. 

• 

Match Column: choose “Date” (the column in sheet to match on)  . This means the node 

will look for the row where the Date value equals the value we provide for Date. 

• 

Value to Match: here we provide the date from our data for the row we want to update. 

Because we likely want to update all rows or at least the latest row, we have multiple items. Actually, 
since we processed every item (each date), we have an array of items with all computed fields. We can 
feed them all into the Google Sheets node in one go. n8n will process each item (row) one by one, 
upserting by date. This is convenient but if there are many, watch out for rate limits (we might want to 
batch or throttle – but if this is done rarely or sheet not huge, should be fine). Google’s write limit is also 
around 60 writes per minute. If we have, say, 250 trading days of data and multiple tickers, that could be 
heavy. Perhaps initially just write the latest row per ticker to avoid enormous writes. But for backtesting, 
writing all historical results is useful one-time. If worried, you can throttle or use a SplitInBatches to update 
in chunks with Wait. 
For demonstration, let’s assume we want to write all the data including indicators to the sheet. That 
means we should have matching columns set up in the sheet or allow mapping automatically. 

• 

Mapping Mode: We can choose Map Automatically to map fields by name. But likely 

the sheet doesn’t have all those columns pre-made. Append or Update might create new columns if 
mapping automatically (not certain if n8n adds new columns or if they must exist). If “Map Automatically”, 
it matches incoming fields to sheet columns by header name. This requires your sheet already has those 
header names. For initial build, you might manually create headers for each new column. Alternatively, 

 
 
 
 
 
 
 
 
 
 
use Map Each Column Manually and then you can specify which column gets which value. But that’s 
tedious for so many columns. 
The quick way: open your Google Sheet, add headers like “SMA20, SMA50, SMA200, EMA20, …, RSI14, 
MACD, MACD_Signal, MACD_Hist, BB_upper, …, VolAvg20, VolRatio, VolSpike, Support60, Resist60, 
StochK, StochD, ATR14, Signal, SignalStrength, BullScore, BearScore”. It’s a lot but you can pare down if 
some aren’t needed. You could at least output the key ones and the signal. 
However, if someone with no experience is implementing, maybe they won’t output everything. The 
question implies to include them, though, perhaps expecting a wide sheet or maybe a separate sheet. 
Since we can’t physically create the sheet here, we instruct them to ensure the sheet has matching 
columns. Then in n8n: 

• 

Set Mapping Column Mode to “Map Automatically” for simplicity (it will match by 

header name). 

• 

Set Column to Match On to “Date” and the Value of Column to Match On to the Date 

field from our data (in the node UI, pick the Date field from the input item as an expression)  . 

• 

For Values to Send, if mapping automatically, you might not need to manually specify 

each – n8n will send all JSON fields. But it’s safer to explicitly list which fields to send (especially if some 
are internal we don’t want). 
In “Values to Send”, you could add each field name mapping to itself. But with dozens of fields, that’s 
lengthy. If the sheet has exactly same headers as JSON keys, auto should just do it. 
We can advise to maybe not include absolutely everything. Possibly at least: Date (for reference), then 
perhaps key indicators like SMA50, SMA200, RSI14, MACD, maybe Stoch or BB or ATR if needed, 
Volume, plus final Signal and Strength. They can always extend. 
Execute the Google Sheets Write Node: 
When you run the workflow, after calculations, the Google Sheets node will iterate through each item 
(each date) and update the sheet. The first time, if your sheet only had OHLCV and not the new columns, 
mapping automatically should create those columns (n8n will add data to new headers if Append or 
Update, I believe, as long as the first row is header row). If it doesn’t, you might need to add headers 
manually first. 
If you set it to upsert, existing rows (matching date) will get new data filled in. If any date wasn’t in original 
(perhaps if original had gaps or if we extended beyond), those would be appended as new rows in date 
order (though append adds to bottom, not sorted – if we needed to sort by date, better to have had them 
beforehand). 
In practice, since we used the same data we read, every date is already in sheet. So it will just update 
each row. 
Confirming in Google Sheets: After execution, open the Google Sheet. You should see new columns 
filled with numbers (indicator values) and the final Signal column showing “Buy”, “Sell”, or “Hold” for each 
date. The last row would have the most recent signal (that’s what you care about for current action). If all 
is well, n8n will have processed multiple tickers if in loop – you might have multiple sheets updated, one 
per ticker. 
If you have one combined sheet for all tickers (with a Ticker column), a different approach is needed (the 
match on would need ticker+date combination), but as we set up separate sheets per ticker, it’s 
straightforward. 
Note on Backtesting: Because we wrote every day’s signal, you can now backtest strategy performance 
by examining what signals were given versus actual price movement. For example, filter the sheet to 
dates where Signal was “Buy” and see what happened in subsequent days, etc. This is manual analysis. 
For a systematic backtest, one could compute profit if following signals (you could add another function to 
simulate trades and tally profit, but that’s beyond scope). However, with this sheet data you can at least 
visually or using formulas analyze win rates. If you wanted, you could add a column “NextDayReturn” or 
such to measure outcome of signals, but again, beyond initial implementation. 

 
 
 
We will mention that now the sheet can be used for backtesting evaluation of the strategy. 
Step 5: Supporting Historical Backtesting 
We have essentially built backtesting support by calculating indicators and signals for historical data. To 
explicitly emphasize this: because our workflow processes the entire price history and produces signals 
for each date, you can examine those past signals against known outcomes. This allows you to evaluate 
the strategy’s performance retrospectively. Here are some ways to do that: 

• 

Visual Backtest in Sheets: In the Google Sheet, you can create a filter on the Signal 

column and look at all dates where Signal was “Buy”. Check what the stock’s price did after those dates – 
did it generally go up soon after (a successful call) or were there many cases it kept falling (a false 
signal)? You can calculate metrics like: if one bought at next open after a “Buy” signal and sold at next 
open after a “Sell” signal, what would the profit be? This can be done by adding formula columns for trade 
P&L. Similarly for “Sell” (which could indicate shorting or exiting long positions). 

• 

Add Backtest Calculations (optional): If you want to automate performance 

measurement, you could expand the workflow. For example, a Function node could simulate a simple 
strategy (like always be in or out based on signals and accumulate returns). However, that is complex and 
possibly beyond a beginner. As a simpler approach, use Excel/Sheets formulas once you have the 
signals. For instance, add a column “StrategyReturn” that if Signal == “Buy”, then computes percent 
change from that date’s close to the next Sell signal’s close. Summing those can give total return. This 
requires some spreadsheet work. The key is the data is there for analysis. 

• 

Use Charting: You could copy Date, Close, and Signal columns into a charting tool or 

use Google Sheets charts, applying green/red markers on buy/sell dates to visually inspect if signals align 
with actual bottoms/tops. This will quickly show if your multi-indicator approach is catching the right 
moves. 

• 

Adjust strategy if needed: Backtesting might reveal, for example, that the strategy gives 

too many false buys in a choppy market. You might then tighten the criteria (e.g., require 3 bullish 
conditions instead of 2, or require a volume confirmation always). Because everything is calculated via 
the Function node logic, you can tweak those rules and rerun on the same data to see how signals 
change. This iterative improvement is a huge benefit of having backtesting support. You can aim to 
maximize past performance (though be careful of overfitting – the goal is a robust strategy, not just one 
that fits history perfectly). 
In summary, to backtest the strategy performance: run the workflow on historical data and examine 
the “Buy” and “Sell” signals it would have generated, using the stored results in Google Sheets. 
Because our workflow processes each date in sequence (and only uses past data for decisions), the 
signals are historically realistic (no future data was used for past signals, avoiding lookahead bias). This 
means the backtest is valid. Evaluate metrics like win rate, average gain per trade, etc., and adjust 
strategy logic in the Function node as needed, then rerun to test again. This ability to refine using 
historical data is crucial to developing a professional-grade strategy. 
Step 6: Error Handling and Workflow Reliability 
A professional system must handle errors and edge cases gracefully so it runs reliably over time. Let’s 
address potential issues and how our n8n workflow mitigates or can be configured to handle them: 
Missing or Incomplete Data: 

• 

If a stock’s Google Sheet has missing days (perhaps no data on a holiday, or some 

blanks), our calculations might encounter null/NaN. We partially addressed this by checking for undefined 
in code (e.g., treating undefined Close as 0 or skipping). To be safe, ensure your input data is clean (no 
empty rows). If some columns like Volume are blank, you might edit them (put 0 or carry forward last 
value if appropriate). Our code usually checks (like parseFloat(item.json.Close || 0)) which can handle 
blank as 0 – but a blank close doesn’t make sense; better to remove that row. 

• 

If not enough data points for an indicator (like a new stock with only 100 days, so 

SMA200 can’t be computed fully), our code sets those early values to null and only starts giving signals 

 
 
 
 
 
 
once enough history accumulated. That’s fine. Just be aware initial period will have Signal = Hold likely 
due to insufficient data (which is realistic – one wouldn’t trade without enough history). 

• 

If a particular indicator fails to compute for some reason (like division by zero – we 

handled most, e.g., Stoch when range=0 we defaulted to 50, RSI when no losses we set RSI=100, etc.), 
the code avoids crashing and continues. If any error in Function node occurs, n8n would stop that 
execution. To guard, you can wrap calculations in try/catch inside the function and set defaults on error. 
But given our careful checks, it should be okay. 
API Rate Limits and Large Data Handling: 

• 

We discussed using a Wait node in the loop for multiple tickers to avoid hitting Google’s 

per-minute quotas. If you loop through many tickers, include a small delay for each. For writing back 
results, if you output hundreds of rows at once, Google Sheets may briefly throttle. Monitor for any “429 
too many requests” or “Quota exceeded” errors in n8n execution. If encountered, you can do the same 
trick: break the output into batches. For example, after generating signals for all days, use a 
SplitInBatches node to send, say, 50 rows at a time to Google Sheets node with a short Wait in between. 
Or simply enable “Retry on Fail” on the Google Sheets write node with a 1000ms wait, so if it hits a quota, 
it waits and retries automatically. 

• 

In our design, reading all rows for a ticker in one go is fine if the sheet isn’t huge (several 

years of daily data is only a few thousand rows, which is fine). But if you had extremely large datasets 
(say minute bars or decades of history), you might need to implement pagination or limit the range read. 
Google Sheets node allows specifying a range (like A1:F5000). But this is usually not an issue for typical 
usage. 
Failed Ticker Processing: 

• 

If one ticker’s data retrieval fails (network issue, or sheet name not found, etc.), we don’t 
want the whole workflow to stop. For the Google Sheets read node, you can enable Continue On Fail (in 
node settings). This way, if it errors (e.g., sheet not found), n8n will treat it as a “soft” error and move on. 
In our loop, that means we should catch that and continue to next ticker. You might insert a check: if 
Google Sheets read returned 0 items or error, use a Function or IF node to skip processing that ticker. 
Logging the error to a separate log (maybe an email or another sheet) would help you notice that ticker 
had an issue. 

• 

Similarly, for the write node, continue on fail could be used, but better to fix root cause 
(like correct columns). A failure in write likely means some configuration mismatch (like a column name 
doesn’t exist and n8n didn’t create it). Double-check the sheet setup if that happens. 
Graceful Degradation: 

• 

We built a robust logic where if data is missing, we output null or Hold signals rather than 

throw error. For instance, first 13 days RSI is null -> no signals in those days, which is fine. 

• 

If volume is zero (holiday), our volume average might be lower for that window but it 

won’t break (just 0 included, which slightly affects avg). 

• 

If any math does go wrong unexpectedly, one could add a global try in each function 

node: 
try { 
  // calculations... 
} catch(e) { 
  $execution.resume(); // (or handle accordingly) 
} 
But since we want quality, better to ensure logic is correct than to hide errors. 
Logging and Notifications: 

• 

In a pro setup, you might want to know when a signal is generated (especially if running 

daily). You could add a node at end that if Signal is “Buy” or “Sell” (for the latest date) and perhaps 
strength above certain threshold, it sends a notification – e.g., an email or a Slack message. That’s 

 
 
 
 
 
 
 
 
 
beyond our core, but n8n makes it easy to add an Email node or similar after the Google Sheets write. 
This way you get alerted to new trade signals in real-time. 

• 

Also log errors: you could add a Catch node in workflow to catch any node errors and 

alert you or log to a “Errors” sheet. But if we set Continue on Fail on potential failing nodes, we might not 
trigger Catch. So design carefully for what approach. 
Maintaining API Limits Over Time: 

• 

If you schedule this workflow to run daily (with a Cron node or using n8n’s Trigger), 

consider that reading an entire sheet daily might be overkill (e.g., reading 1000 rows every day). Instead, 
you could optimize: read only the latest row (there’s ways to query a specific range). But since 1000 rows 
is not much, it’s likely fine. If you had an extremely large sheet, you might split historical and current. 
Google’s per-day quota is also something (like 5000 requests per day maybe). Our 

• 

design uses very few requests (one read per ticker, one write per ticker per run). If running daily with, say, 
10 tickers, that’s 20 requests/day, well under limits. 
Conclusion of Error Handling: 
By implementing these measures – using Wait nodes for rate limits, enabling Retry on Fail for transient 
errors, using Continue on Fail for non-critical nodes, validating data, and logging important events – the 
workflow will be resilient. It will not crash due to a single missing value or a slight API delay. Instead, it will 
either self-correct (retry/wait) or skip and move on, ensuring that one problematic ticker or day doesn’t 
prevent the rest of the analysis from completing. 
Finally, with everything set up, you have a robust n8n workflow that automates professional technical 
analysis: it fetches data, computes a rich set of indicators (with sound financial reasoning behind each), 
generates buy/sell signals with multi-indicator confirmation (minimizing false signals through redundancy 
and volume confirmation), writes the results for record-keeping and review, and allows you to backtest 
and refine the strategy. 
By following this step-by-step guide, even someone new to n8n or trading algorithms can implement a 
complex technical analysis system and use it to make more informed trading decisions. Happy 
automating and trading!
