# Phase 1 Automated Stock Analysis Platform – Setup Guide

> Imported from: `/Users/kyleholthaus/Downloads/repoLAI Docs /Phase 1 Automated Stock Analysis Platform – Setup Guide.pdf`
> Converted: 2025-09-11 21:33:30

• 
stored data, etc.). 
• 

Phase 1 
Automated Stock Analysis Platform – Setup Guide 

This guide will walk you through setting up an end-to-end stock analysis platform using n8n for automated 
data workflows and Streamlit for an interactive dashboard. We will use n8n.cloud to host our automation 
workflows, Streamlit Community Cloud to host the dashboard app, and Google Sheets as the primary 
data storage (with notes on scaling to PostgreSQL). Security is emphasized throughout – we’ll configure 
both OAuth and service account access for Google Sheets and manage API keys via secure methods. By 
the end of this guide, even a beginner will have a working system that monitors key stocks (NYSE, 
NASDAQ, etc.), pulls in relevant news with sentiment analysis, and presents it on a Streamlit dashboard. 
Overview of Components: 

• 

n8n.cloud: Hosted automation service to fetch stock prices and news on a schedule, 

writing results to Google Sheets. 

Google Sheets: Serves as a database and configuration (list of stock tickers to monitor, 

Streamlit Cloud: Hosts the dashboard app that reads from Google Sheets (or a 

database) and displays stock metrics and news sentiment. 

• 
• 

Alpha Vantage & NewsAPI: Third-party APIs for stock market data and news articles. 
Python 3.9+ environment: For building the Streamlit app and any custom analysis code, 

using latest library versions. 

• 

Security: OAuth or service account for Google API access, environment secrets for API 

keys, and best practices to avoid exposing credentials. 
Let’s dive into the detailed setup. 
1. Setting Up Required Accounts 
Before building the workflows and app, you need accounts and API credentials for all services: 
1.1 n8n.cloud Account 
Sign Up and Choose a Plan: Go to n8n.cloud (the official hosted service for n8n) and sign up for a new 
account. n8n offers a free trial for new users  – you can start with the trial (no credit card required initially) 
and later choose a paid plan if needed. During sign-up, provide your email, set a password, and verify 
your email if prompted. After login, you’ll land on the n8n Cloud dashboard. 
Creating an Instance: On the n8n cloud dashboard, you may need to create an instance (workspace) if 
one isn’t created by default. Follow the UI prompts to set up your n8n instance (you might be asked to 
choose a subdomain or name for it). For example, you might get an instance URL like 
https://your-workspace.n8n.cloud/. 
Navigating the UI: Once your instance is running, click “Go to Editor” or a similar button to open the n8n 
workflow editor in your browser. You should see a blank canvas where you can create workflows. 
Familiarize yourself with the editor: on the left, there’s a “Nodes” panel (listing integrations), on the top a 
menu (for saving, executing, etc.), and the main area is the canvas where you’ll add nodes. 
Select a Plan if Necessary: The free trial is time-limited, so if you intend to run this long-term, consider 
selecting a plan in the Billing/Plans section of your n8n.cloud account settings. The Free tier (if available 
beyond trial) may have limits on workflow execution frequency or active workflows – ensure it’s sufficient 
for your needs (e.g. some free tiers limit to a certain number of workflows or executions per day). For 
heavy use (monitoring many stocks frequently), you may need a paid tier. 
Create a New Workflow: In the n8n Editor UI, click “New Workflow” (usually a button on the top right or 
in the sidebar). An untitled workflow will open. Click the workflow name (top of the canvas) to rename it to 
something like “Stock Analysis Workflow”. This workflow will later be configured to fetch stock data and 
news. 
Configure n8n API Credentials (Overview): We will set up credentials in n8n for Google Sheets, Alpha 
Vantage, and NewsAPI in later steps. n8n has a Credentials store – think of it as a vault for API keys and 

 
 
 
 
 
 
 
auth tokens. For now, locate the Credentials section in n8n: click the key icon on the left sidebar (or go to 
Settings -> Credentials). You’ll add new credentials here for each service as we proceed. 
Expected Outcome: By this point, you should have an active n8n cloud account with an instance running 
and ready. You should be able to open the editor (a blank workflow canvas). No workflows exist yet, but 
you’re ready to create them. 
Validation: To confirm everything is ready, try adding a simple node as a test (e.g., add a “Start” node 
from the nodes list and a “NoOp” node) and click “Execute Workflow” in test mode. It should run 
immediately (doing essentially nothing in this test) with a green success indicator. This just confirms your 
instance is functioning. If you encounter any errors starting the workflow or an inability to create nodes, 
double-check that your instance is active (restart it from the cloud dashboard if needed). 
Troubleshooting: If the editor won’t load or you see a “instance not available” error, ensure you have 
started your n8n instance in the cloud dashboard. If sign-up links aren’t working, try an alternative 
browser. For any persistent platform issues, n8n’s documentation and support forums are a great help. 
1.2 Google Sheets API (Google Cloud Setup) 
To allow n8n (and optionally your Streamlit app) to read and write Google Sheets, you need to configure 
Google API credentials. There are two methods to authenticate with Google Sheets: 

• 

OAuth2 (User Authentication): Allows n8n to act on behalf of your Google account via 

a consent screen. This is easier to set up for personal use and uses your own account permissions. 

• 

Service Account (Server-to-server): A dedicated account for applications with its own 

credentials JSON. This is ideal for headless operation (no manual login) and for production, but setup is a 
bit more involved. 
We will set up both methods so you can choose what fits best. (You can use OAuth2 during initial 
development and then switch to a service account for long-term runs if desired.) 
1.2.1 Enable Google APIs and Create a Project: 

1. 

Go to the Google Cloud Console: https://console.cloud.google.com/ and log in with your 

Google account. If you haven’t used it before, you may need to accept terms and create a project. 

2. 

Create a new Project in Google Cloud for this platform (for example, 
“StockAnalysisProject”). In the top menu, click the project dropdown and select “New Project”. Enter a 
project name and organization (if applicable), then Create  . Ensure the new project is selected (check the 
top bar – it should show your project’s name). 

3. 

Navigate to APIs & Services -> Library in the Cloud Console. Enable the APIs we need: 

search for Google Sheets API and click Enable, and also enable Google Drive API . (The Sheets API 
actually uses Drive API under the hood for some file access, so it’s recommended to enable both .) If you 
plan to use other Google services, enable them now as needed. You should now have the needed APIs 
enabled on your project. 
OAuth2 Method: Setting Up OAuth Consent and Credentials 
If using OAuth (which is suited for a single user’s Google Sheets, e.g., your personal Google account): 

4. 

In the Cloud Console, go to APIs & Services -> OAuth consent screen. Choose User 

Type External (for personal Google accounts; Internal is only if you have an organization GSuite domain)  
. Click Create. 

5. 

Fill in the App name (e.g., “Stock Analysis n8n”), User support email, and developer 
contact email (usually your email) . For scopes, you can skip adding any scopes manually here – we’ll 
request specific scopes in n8n. Google requires an authorized domain since this is an External app: add 
n8n.cloud to Authorized domains (because n8n.cloud will handle the OAuth redirect) . This tells Google 
that n8n.cloud is allowed in the OAuth flow. 

6. 

Save and continue through the consent screen setup (you don’t need to add test users if 
you’re using your own account as the developer and user – your account will automatically be allowed to 
authorize since it’s in testing mode). You might see a summary page – just review and finish. The app will 

 
 
 
 
 
 
 
 
be in “Testing” status by default, which is fine (it means the OAuth token validity is 7 days in testing, 
renewable by re-authenticating) . 

7. 

Now go to APIs & Services -> Credentials. Click Create Credentials -> OAuth client 
ID . Choose Application type: Web application . Give it a name like “n8n OAuth Client”. In Authorized 
redirect URIs, copy-paste the redirect URL from n8n. In your n8n Credentials setup (we’ll open that 
next), when you select Google OAuth2, it will show a Redirect URI. On n8n.cloud, the redirect is usually 
https://oauth.n8n.cloud/oauth2/callback (which is the generic n8n cloud OAuth proxy) – this is the URI you 
must add . To be sure, in the n8n editor, add a new credential for Google (choose “Google Sheets API” or 
“Google OAuth2 API” credential) and it will display the exact redirect URL to use. Copy that and paste it 
into the Authorized redirect URIs field, then Create . 

8. 

After clicking Create, Google will show you a dialog with a Client ID and Client Secret. 
Copy these values. Now, go to n8n Credentials in the editor. Click New Credential and choose Google 
Sheets (if available) or Google OAuth2. There are two Google credential types in n8n: “Google Sheets 
API” (single-service) and a more general “Google OAuth2”. If using single-service, the scopes are preset 
for Sheets; if using generic, you can specify scopes. For simplicity, choose Google Sheets credential in 
n8n. It will ask for the Client ID and Client Secret – paste the ones you just obtained . It might also show 
the scopes it will request (ensure it includes Sheets and Drive scopes like .../auth/spreadsheets and 
.../auth/drive.file). 
9. 

Click “Connect” or “Sign in with Google” in the n8n credential modal . This will open a 

Google OAuth popup – select your Google account, and you’ll see a consent screen asking you to allow 
access to Google Drive and Sheets. Since the app is unverified (in testing), Google will show a warning 
“Google hasn’t verified this app”. This is expected. To proceed, click Advanced and then “Go to (your 
app name)” to continue authorization . Then click Allow to grant permissions. 

10. 

If everything is set up correctly, the n8n credential should now show as Authenticated (a 
green check or similar). Save the credential in n8n. This OAuth credential will allow n8n to read/write your 
Google Sheets. 
Expected Outcome (OAuth): You have a Google OAuth2 credential saved in n8n (under Credentials, 
e.g., “Google Sheets (OAuth)”) that is connected to your Google account. In Google Cloud, you have an 
OAuth client associated with your project. You can now use Google Sheets nodes in n8n with this 
credential to access your spreadsheets. 
Validation: In n8n, create a quick test workflow: Add a Google Sheets node, set its credentials to the 
one you just created. In the node, select an operation (like “List Sheets” or “Read Spreadsheet” if you 
have one). For now, if you don’t have a spreadsheet ID handy, just ensure the credential is selectable and 
no error appears. (We will fully test this after creating the spreadsheet in section 2). If the credential 
wasn’t set up right, n8n would show an error when you try to use it. Common errors include “access 
denied” if the OAuth scopes are wrong or the token expired – if so, double-check steps and try 
re-connect. Remember, in testing mode the token lasts 7 days, after which you’d need to re-auth (or 
publish the app if you want long-lived refresh tokens). 
Troubleshooting OAuth: 

• 

If Google’s consent screen says “Error 400: redirect_uri_mismatch”, it means the 

Redirect URI wasn’t entered exactly as required. Fix: go back to Google Cloud Console, edit your OAuth 
Client and add the correct redirect (ensure no whitespace and that it matches what n8n shows, e.g., 
https://oauth.n8n.cloud/oauth2/callback). 

• 

If n8n credential says “Could not retrieve access token” or similar, ensure the consent 
screen is configured and you allowed the scopes. If your Google Cloud app is still in testing and you’re 
using a different Google account to log in than the one that created the app, you must add that account as 
a test user in the OAuth consent screen settings. 

 
 
 
 
 
 
• 

If you see “Google hasn’t verified this app” each time, that’s normal in testing. You 
could submit your app for verification if this were a production multi-user app, but for personal use you 
can ignore the warning. 

• 

If after 7 days the OAuth token expires (due to testing mode), you’ll need to re-open the 

n8n credential and click Connect again to reauthorize. To avoid this, you’d have to publish the app 
(requires going through Google’s verification, which is not necessary for a small internal project). 
Service Account Method: Creating a Service Account 
Alternatively (or additionally), set up a Google Service Account for headless access. A service account 
is like a robot user that can be authorized to access Google APIs. 

11. 

In Google Cloud Console, go to APIs & Services -> Credentials again. Click Create 

Credentials -> Service Account. In the Service Account creation form, give it a name (e.g., “n8n Sheets 
Service Account”) . You can skip assigning roles for now (no role is strictly needed to access Sheets API, 
since we will directly share the document). Just create the service account. 

12. 

After creation, you’ll see the new service account listed. Click on it to open details. Find 
the “Keys” section and click “Add Key -> Create new key”. Choose JSON and click Create. This will 
download a JSON file to your computer – this is the private key and credentials for the service account. 
Keep it safe! (It contains a private key; do NOT commit this file to any repository.) 

13. 

Now, open the JSON file in a text editor. In n8n, create a new Credential: choose Google 

Service Account (or specifically “Google Sheets Service Account” if available, but generally n8n’s 
Google Service Account credential works for any Google API). In the credential form, there will be fields 
for Service Account Email and Private Key. From the JSON, copy the value of the "client_email" field 
and paste it into Service Account Email . Then copy the "private_key" value – be careful to copy 
everything between the -----BEGIN PRIVATE KEY----- and -----END PRIVATE KEY----- lines (excluding 
those markers). In n8n, paste this into the Private Key field . (Do not include the quotes or \n escape 
characters; n8n might accept it as-is or you may need to replace literal \n with actual newlines – newer 
n8n versions handle it automatically.) 

14. 

Impersonation (optional): n8n might show an option “Impersonate a User” for Google 

service accounts. You can ignore this (it’s used for domain-wide delegation in GSuite environments) . We 
won’t use domain-wide delegation here, so leave impersonation off. 

15. 

Click Save on the service account credential. There is no “Connect” step because it 

doesn’t require interactive auth. The credential should save successfully if the email and key were correct. 
Share the Google Sheet with the Service Account: The service account is like a separate user 
identified by that client_email (which looks like [email protected]). By default, it has no access to your 
personal Google Drive files. To allow it to work on your Google Sheet, you must share the spreadsheet 
with the service account’s email . We’ll do this after we create the spreadsheet (in Section 2). Keep the 
service account email handy or remember to come back to this step when the sheet is ready. (In Google 
Drive, you’d add the service account email as a collaborator on the file, typically giving it Editor 
permission if you want it to write data.) 
Expected Outcome (Service Account): You have a Google Service Account credential saved in n8n, 
containing the email and private key from the JSON. Once the target Google Sheet is created and shared 
with this email, n8n will be able to access it without further manual OAuth steps. 
Validation: We will test the service account’s access once the Google Sheet is set up (by using a Google 
Sheets node with this credential to read/write data). Without sharing the sheet, any attempt to access will 
result in a 403 error, so don’t be alarmed if you test now and get “permission denied” – it just means you 
need to share the sheet to that email. We’ll cover that soon. 
Troubleshooting Service Account: 

• 

If n8n throws an error upon saving the credential, double-check formatting of the private 

key. A common mistake is including the quote marks or not preserving the newline characters. In older 
n8n versions, you needed to manually replace \n with actual new line breaks in the Private Key field . In 

 
 
 
 
 
 
 
 
newer versions, it may accept the pasted string with \n. The safest route: open the JSON in an editor, 
copy the multi-line key as-is (without quotes) and paste into the field. 

• 

If you later get “403 Forbidden” errors using the Sheets node with this credential, it likely 
means the service account doesn’t have access to the spreadsheet. The solution is to share the file with 
the service account’s email (or if using Google Workspace, ensure domain delegation if trying to access 
user files – not our case here) . 

• 

Remember that a service account is separate from your personal Google account. The 

spreadsheet either needs to be owned/created by the service account (complicated since it’s not 
straightforward to create a Sheet on a service account in Drive without API calls) or simply shared to it by 
you (easiest). We’ll do the latter. 
Now you have both authentication methods available in n8n. You can use one or the other in the Google 
Sheets node credentials dropdown. (In n8n, you’ll see your credential names – e.g., “Google Sheets 
OAuth (your-email)” and “Google Sheets Service Account”. You can test both later to decide which to rely 
on. Many prefer service accounts for server automations to avoid token expiration issues.) 
1.3 Streamlit Cloud Account 
Streamlit Community Cloud allows you to deploy your Streamlit app online easily. It requires a GitHub 
account to host your code. Here’s how to set it up: 
Sign Up / Log In: Go to Streamlit Community Cloud: https://share.streamlit.io/. Click “Continue to sign 
in” and choose “Sign in with GitHub”. (If you don’t have a GitHub account, create one first at 
https://github.com.) Authorize Streamlit to access your GitHub – you’ll see an OAuth prompt on GitHub 
asking for permissions. Click “Authorize streamlit” to allow access . By default, Streamlit needs at least 
read access to your repositories (and if you want to deploy from private repos, you’d grant that 
specifically). After authorization, you’ll be redirected to Streamlit Cloud. 
Create a New App Deployment: Streamlit will present your Workspace (the dashboard for your apps). 
Since this is likely your first app, you’ll see a message like “No apps to show… Deploy one now”. To 
deploy, click the “Create app” button (top right). A form will appear to set up the deployment. 
Link to GitHub Repository: In the deployment form, under Repository, select your GitHub username 
and repository from the dropdown. (If you just created the repo, it should appear; if not, you might need to 
refresh or ensure Streamlit has access to that repo). Choose the branch (usually “main” or “master”) and 
then enter the Main file path, e.g., app.py (or whatever your Streamlit script filename is). Essentially, you 
are telling Streamlit which file to run. For example, if your GitHub repo is username/stock-analysis and 
your Streamlit script is dashboard.py in the repo root, you’d select that repo, branch “main”, and main file 
path dashboard.py. The Streamlit interface makes this easy by listing options. Example: Repository: 
your-github-username/stock-analysis-dashboard, Branch: main, Main file path: app.py. 
Optionally, you can choose a custom subdomain for your app in the App URL field. For example, you 
might put “stock-demo” – then your app will be accessible at https://stock-demo.streamlit.app. If you leave 
it blank, Streamlit will generate one (often based on your repo name or a random adjective-noun combo). 
At this point, you’ve essentially done the three steps Streamlit Cloud needs: “1. Sign in with GitHub, 2. 
Pick a repo/branch/file, 3. Click Deploy!” . 
Advanced Settings (Secrets and Python version): Before clicking Deploy, click on “Advanced 
settings” in the deployment dialog. Here you can set the Python version and, importantly, add secrets. 
Streamlit Cloud supports Python 3.9, 3.10, 3.11, etc. It defaults to the latest stable (currently 3.12, but you 
may choose 3.10 or 3.11 if some libraries have issues with the latest) . Select Python 3.9+ (anything 3.9 
or higher is fine; for example, choose 3.10 if available, since our code will run on 3.9+). Next, in the 
Secrets field, you can paste your secret variables. We will prepare a secrets.toml file later with content 
like API keys; you can paste that content here. For now, you might skip adding secrets until we define 
them in Section 3, but remember this is where you’ll input things like ALPHAVANTAGE_KEY, 
NEWSAPI_KEY, etc., so that they are available to your app securely. 
After setting this up, click “Save” to close advanced settings. 

 
 
Deploy the App: Now click “Deploy”. The app will go into a building state – you’ll see logs as Streamlit 
Cloud installs dependencies from your requirements.txt. The first deploy can take a minute or two. If 
everything installs and the app launches, you’ll see “Your app is live” and it will open at the given URL. 
 Streamlit’s deployment process is simple: sign in, pick your repo/branch, and deploy – subsequent git 
push updates will auto-deploy the changes.  
Expected Outcome: Your Streamlit app (though not fully coded yet) is deployed on Streamlit Cloud. You 
should have a URL like https://your-app-name.streamlit.app. At this moment, if the code is incomplete or 
waiting for data, the app might show errors or a placeholder. That’s okay – we’ll be writing the app code 
soon. The main thing is that the deployment pipeline is working. 
Validation: In Streamlit Cloud’s dashboard, you should see your app listed, with a green dot if running. 
Click the app to open it. If you see Streamlit’s default “Hello World” (if you left the default code) or an error 
from missing code, that’s expected until we develop the app. The key validation is that there are no 
deployment errors. If the app failed to deploy due to dependency issues, click “Deploy Logs” to inspect. A 
common successful sign is seeing “🎈 Running on external URL: …streamlit.app” in the logs and then the 
interface appears. 
Troubleshooting Streamlit Cloud: 

• 

If the app fails to deploy, check that you have a requirements.txt in the repo specifying 

needed libraries. Without it, Streamlit may only have base packages and your app’s import statements 
could fail. If you see import errors in the log (e.g., “No module named streamlit” or “alpha_vantage not 
found”), add those to requirements and push to GitHub. Streamlit Cloud will auto-redeploy on push. 

• 

If your GitHub repo isn’t listed or you get an auth error linking GitHub, ensure you 

authorized Streamlit’s GitHub app properly. You can reconnect by going to your Streamlit workspace 
Settings -> Linked accounts and verify GitHub is connected . Also, you must have admin rights to the 
repo (if you created it, you do). 

• 

If you need to deploy from a private repo, you must give Streamlit access to private 
repos. In the GitHub auth prompt, ensure you allowed either “all repos” or specifically granted the app 
access to the one. You can adjust this in GitHub settings under Applications. (Alternatively, make the repo 
public if possible, since Community Cloud apps are meant to be shareable.) 

• 

Secrets not found: If you attempt to use st.secrets["MY_KEY"] in code and it’s returning 

a KeyError, ensure you actually added the secret in the app’s settings. You can do this even after 
deployment: in your Streamlit workspace, click the three dots (…) next to your app, choose Settings -> 
Secrets. There you can add or edit secrets. After adding, reboot the app. We’ll detail secret formatting in 
Section 3. 
• 

App access control: By default, Streamlit Community Cloud apps are public (anyone 

with the URL can view). If you want to restrict who can view it, Streamlit allows you to set an email 
allowlist in the app settings (under “Share app” or similar, you can invite specific email addresses). This 
requires the viewer to log in with those emails. If you’re just using it yourself or within a small group, you 
might not need this, but it’s good to know it exists for security. 
1.4 Alpha Vantage & NewsAPI Accounts 
We will use Alpha Vantage for stock data and NewsAPI for news headlines. Both require obtaining API 
keys: 
Alpha Vantage: 
• 

Go to the Alpha Vantage website and click “Get Your Free API Key”. Sign up with your 

email (and name). Upon signing up, you’ll immediately get an API key (it’s shown on the website and also 
sent to your email). The key is a 16-character alphanumeric string. 

• 

Note the rate limits: Alpha Vantage’s free tier allows 5 API requests per minute and 
500 requests per day . This is sufficient for a modest number of stocks if you space requests (e.g., you 
can fetch 5 stocks per minute). If you exceed this (for example, looping through too many tickers too fast), 

 
 
 
 
 
 
 
you’ll get a "message": "frequency limit exceeded" error. We will design workflows to respect these limits 
(by scheduling or using delays if needed). Keep the key handy; we’ll store it securely later. 
NewsAPI: 

• 

Go to NewsAPI.org and sign up for a free developer account. Once signed in, go to your 

Account or Get API Key section – you’ll see your API key (a 32-character string). 

• 

Free tier limitations: NewsAPI’s developer (free) plan permits 100 requests per day , 

and note it returns news with a 24-hour delay (news articles won’t include the most recent 24h). This is 
acceptable for a development/testing scenario. If you need real-time news, NewsAPI requires a paid plan. 
For our purposes, 100/day is plenty (we might fetch news a few times a day for a handful of stocks). 

• 

Keep this API key secure as well. 

Store API Keys Securely: Important: Do not hard-code these keys in your code. We will use 
environment variables or Streamlit secrets to manage them. For now, just copy them to a safe place (or 
into a local .env or secrets.toml file which we’ll set up in Section 3). Remember that if someone finds your 
API keys, they could misuse your quota or data, so treat them like passwords. 
Test the APIs (Optional): It’s good practice to test your keys with a simple request to ensure they work: 

• 

For Alpha Vantage: Open a browser and use a sample endpoint, for example: 

https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=IBM&apikey=YOUR_KEY. 
Replace YOUR_KEY with your key. You should get a JSON response with stock data for IBM. If you see 
an error about the key, double-check the key string. Keep in mind the 5-per-minute limit – don’t refresh 
too quickly. 

• 

For NewsAPI: Try a sample query in browser or using curl. For example: 

https://newsapi.org/v2/everything?q=Apple&apiKey=YOUR_KEY. This should return JSON with some 
articles about Apple (likely delayed news given free tier). If you get an error about API key, ensure it’s 
correct. NewsAPI might also require &language=en to filter English, but not mandatory. 
Rate Limits and Usage Strategy: Given the limits, plan your usage. For instance, if monitoring 10 
stocks, you might schedule the stock price workflow to run every 15 minutes, fetching one stock per 
minute (10 stocks ~ 2 minutes of API calls – well within 5/minute limit). Or fetch them sequentially with 
short delays. For news, you could fetch for all 10 stocks 2-3 times per day (10 requests * 3 = 30 < 100 
daily limit). We will incorporate these considerations in n8n workflows. 
Troubleshooting API Sign-up: Usually straightforward. If the Alpha Vantage site doesn’t show a key 
after sign-up, check your email (including spam) for a message from them. NewsAPI key is usually shown 
on the account page. Neither requires credit card for the free tier. 
1.5 GitHub Repository for Your Code 
To deploy the Streamlit app, you need your code in a GitHub repository. We also recommend 
version-controlling any workflow code or notes via GitHub. 
Create a Repository: On GitHub, create a new repository (e.g., name it “stock-analysis-dashboard”). It 
can be public or private (if private, remember to grant Streamlit access). Initialize it with a README if you 
like, or you can create an empty repo and push code from your local machine. 
Local Repo Setup: If you’re coding on your local machine, you’ll want to clone this repo. E.g., git clone 
https://github.com/yourusername/stock-analysis-dashboard.git. Place your Streamlit app code in this repo 
directory. 
Recommended Repo Structure: 

• 

The root of the repository should contain your main Streamlit app script (e.g. app.py or 

dashboard.py). This is the file you specified in Streamlit Cloud. 

• 

Include a requirements.txt file listing all Python dependencies (one per line). We’ll 

populate this with libraries like streamlit, pandas, alpha_vantage, newsapi, etc. For example: 
streamlit>=1.24   
pandas>=1.5   
requests>=2.28   

 
 
 
 
 
 
 
alpha_vantage>=2.3.1   
newsapi-python>=0.2.7   
vaderSentiment>=3.3.2   
(We will refine this list in Section 3 when setting up the environment. Using >= ensures latest stable 
versions are installed, which is generally good practice unless you need a specific version.) 

• 

A .gitignore file to exclude files like secrets or environment files. At minimum, put lines to 

ignore .env, .streamlit/secrets.toml, any credential JSON files, and pycache directories. 

• 

Optionally, you can organize code into modules: e.g., a utils/ folder with data_fetch.py, 

analysis.py etc., but this is up to you. For a simple project, you might keep most code in the main app file 
for simplicity. 

• 

A README.md explaining your project (optional, but good practice). 

Push Code to GitHub: After adding your files, do the standard Git steps: git add ., git commit -m "Initial 
commit", and git push origin main (assuming you set the remote to your GitHub repo and are on the main 
branch). Verify on GitHub’s website that your files appear. 
Connecting to Streamlit: We already connected Streamlit to the repo in section 1.3. If you pushed new 
changes, Streamlit should auto-deploy the update (you’ll see a “Updating…” status). If not, you can trigger 
a redeploy from the Streamlit app page. Ensure that after pushing, the requirements.txt triggered a fresh 
installation on Streamlit Cloud (check the app logs for installation of the packages you listed). 
Security – Do NOT commit secrets: It’s worth stressing: Never commit API keys, service account 
JSONs, or passwords to Git! This is a common mistake by beginners. Even in private repos, it’s risky. 
We will use the Streamlit secrets mechanism and n8n credentials instead. As a double-check, open your 
repository on GitHub and scan that none of the files (especially app.py or others) contain raw API keys or 
sensitive info. If they do, remove them, push the changes, and revoke/regenerate those keys if they were 
exposed publicly. (Our guide is structured to avoid this altogether.) 
Expected Outcome: A GitHub repo containing your Streamlit app code and config. Streamlit Cloud is 
linked to it and able to deploy it. Now all pieces (n8n, Google API credentials, API keys, code repo, 
Streamlit) are set up and connected. 
Validation: Think of this as the foundation – if you log into n8n, Google Cloud, NewsAPI, Alpha Vantage, 
GitHub, and Streamlit Cloud, everything should be in a ready state: 

• 
• 

n8n: has credentials ready for Google and soon we’ll create workflows. 
Google Cloud: has the project and credentials we created (you can see your OAuth client 

and service account in the console). 

• 
• 
• 
• 

Google Sheets: we haven’t created the actual spreadsheet yet – that’s next. 
GitHub: has your code (maybe just a template for now). 
Streamlit: app is set up (even if it’s a placeholder waiting for data). 
API providers: keys in hand and tested. 

If all good, let’s proceed to configure the Google Sheet and n8n workflows. 
2. Configuring Google Sheets 
Google Sheets will act as our primary datastore and configuration for stocks. We’ll create a spreadsheet 
with specific tabs for input and output data. This section covers how to set up the sheet structure, connect 
it with our credentials, and best practices for organizing the data (plus how to scale or migrate to 
PostgreSQL later if needed). 
2.1 Spreadsheet Structure 
Create the Spreadsheet: Log in to your Google account and open Google Sheets. Create a new blank 
spreadsheet (go to https://docs.google.com/spreadsheets and click Blank). Rename it something 
identifiable, e.g., “Stock Analysis Data”. 
We will use multiple sheets (tabs) within this spreadsheet for different purposes: 

• 
• 

Config/Watchlist Sheet – a sheet for the list of stocks to monitor. 
Data Sheet – a sheet to store stock price data and indicators. 

 
 
 
 
 
 
 
 
 
 
 
• 

News Sheet – a sheet to store news headlines and sentiment. 

You can use any names for these sheets, but for clarity, let’s name them “Stocks”, “Prices”, and 
“News” respectively. Google Sheets by default has a sheet named “Sheet1” – double-click that tab and 
rename to “Stocks”. Then click the + to add two more sheets, naming them “Prices” and “News”. 
Stocks (Watchlist) Sheet: 
This is where you list the ticker symbols (and possibly company names) for the stocks you want to track. 
In cell A1, type “Ticker”. In cell B1, type “Company Name”. These are header labels. 
Starting from row 2 downwards, list the stock symbols in column A and their 

• 
• 

corresponding company names in column B. For example: 
A2: AAPL , B2: Apple Inc. 
A3: GOOGL , B3: Alphabet Inc. 
A4: MSFT , B4: Microsoft Corporation 
…and so on for any stocks of interest. You can include NYSE symbols as well (e.g., TSLA for Tesla on 
NASDAQ, GE for General Electric on NYSE – the API will generally figure out the exchange from the 
symbol if it’s unique, but Alpha Vantage covers most major exchanges by symbol). 

• 

This list is configurable – to add or remove stocks, you’ll edit this sheet. Our n8n 

workflow will be set to read all tickers from here so it’s dynamic. Keep the list reasonable in length to stay 
within API limits (perhaps 10-20 symbols to start). 
Prices (Data) Sheet: 
This will store the numerical stock data (prices, volumes, etc.) and any technical indicators. We need to 
design what columns to include. For a simple analysis, we might store daily prices and perhaps a couple 
of indicators like daily change or moving average. For demonstration, let’s capture: 

• 

Date, Ticker, Open, High, Low, Close, Volume, and perhaps one technical indicator like 

50-day average or RSI. You can always expand this later. 
In row 1 of “Prices” sheet, create headers: 

• 

A1: Date, B1: Ticker, C1: Open, D1: High, E1: Low, F1: Close, G1: Volume, H1: Indicator (this 
“Indicator” column could be repurposed for something like RSI or any metric you choose to compute). 

• 

We will have n8n fill this sheet. Likely each day or each fetch interval, a new row (or set 
of rows) will be appended. For instance, if we fetch daily data for 5 stocks, we might append 5 new rows 
(one per stock with the latest date). Or if we fetch full historical series initially, we might append multiple 
rows per stock. The exact usage depends on how we set up n8n (you could either continuously append 
new data for each day or always overwrite the latest values – appending gives you a time series history; 
overwriting would just keep one row per stock with latest price). 

• 

We will proceed with an append model (so we build a historical dataset). That means 
this sheet will grow over time. Keep an eye on Google Sheets limits (which are quite high – ~5 million 
cells) if you run this for years or with many stocks. For moderate use, it’s fine. 
News Sheet: 
This will store news articles and sentiment analysis results for each stock. 

• 

In “News” sheet row 1, set headers: 

A1: Ticker, B1: Headline, C1: Source, D1: Date, E1: Sentiment. 

• 

We will have n8n or our Streamlit app fill this in whenever we fetch news. Each relevant 

news article will be a row. For example, if AAPL has a news piece: Ticker = AAPL, Headline = “Apple 
launches new product…”, Source = “CNN”, Date = 2023-05-01, Sentiment = 0.8 (we might store a 
sentiment score between -1 and 1). 

• 

This sheet will also grow as we add news entries. We might choose to limit it (e.g., only 
store the latest X articles per stock to avoid endless growth). A simple way is to periodically clear out old 
news or maintain only, say, the last 50 entries per stock – but that can be done manually or via script later. 
Initially, don’t worry; just collect what you need. 
Formatting and Data Types: 

 
 
 
 
 
 
 
 
 
 
 
• 

It’s helpful to format the header row with bold text. Highlight row 1 of each sheet and click 

Bold. This is just visual. 

• 

For the “Date” column in Prices and News, set the number format to Date (Google should 

auto-detect if you enter as yyyy-mm-dd, but you can explicitly format it via Format -> Number -> Date). 

• 

For “Close” or other price columns, you can format as Number or Currency if desired 

(though if mixing stocks with different currencies, maybe leave as plain number). Not crucial, since 
Streamlit will handle display. 

• 
• 

Volume can be a plain number with no decimal. 
The “Sentiment” column could be a decimal number (it will likely be between -1 and 1 if 

using a typical sentiment analyzer). You can format it to 2 decimal places for readability. 
Double-check Sheet Names: We will reference these sheet names exactly in n8n and Streamlit. 
“Stocks”, “Prices”, “News” – ensure they are spelled exactly (case-sensitive). If you use different names, 
adjust accordingly in your workflow and code. 
Example Layout Recap: 
Stocks sheet: 
Ticker | Company Name   
AAPL   | Apple Inc.   
GOOGL  | Alphabet Inc.   
MSFT   | Microsoft Corporation   
... etc. 
Prices sheet: 
Date        | Ticker | Open   | High   | Low    | Close  | Volume    | Indicator   
2023-05-01  | AAPL   | 170.00 | 172.50 | 168.00 | 171.40 | 100000000 | 1.5   
2023-05-01  | GOOGL  | ...    | ...    | ...    | ...    | ...       | ...   
...  
(Indicator here could be something like daily % change or RSI; 1.5 is just a placeholder example.) 
News sheet: 
Ticker | Headline                                 | Source    | Date       | Sentiment   
AAPL   | Apple launches new iPhone                | TechCrunch| 2023-05-01 | 0.7   
AAPL   | Opinion: Apple's stock is undervalued    | Bloomberg | 2023-04-30 | 0.2   
GOOGL  | Google announces AI breakthrough         | CNBC      | 2023-05-01 | 0.9   
...   
You don’t need to pre-fill the Prices or News sheets – they will be filled by automation. But it might be 
useful to add one manual row of dummy data to test your Streamlit app layout. For example, add a 
sample row in Prices and News for one ticker so that something is there to display. Just ensure if it’s 
dummy, you later remove or overwrite it with real data. 
2.2 API Access Setup in Google Sheets (OAuth vs Service Account) 
Now that the spreadsheet is structured, we need to connect our Google API credentials (from section 1.2) 
to this specific spreadsheet. 
Retrieve the Spreadsheet ID: Open your Google Sheet in a web browser. Look at the URL. It will be 
something like https://docs.google.com/spreadsheets/d/<LONG_ID>/edit#gid=0. Copy the long ID 
between /d/ and /edit – that’s the Spreadsheet ID . For example, in 
https://docs.google.com/spreadsheets/d/1A2B3C4D5E6F7G8H9I0J/edit#gid=0 
the ID is 1A2B3C4D5E6F7G8H9I0J. We’ll use this ID in n8n and Streamlit to identify the sheet. 
Share with Service Account: If you plan to use the service account credential in n8n, now share the 
spreadsheet with the service account’s email. Click the green Share button on the sheet (top right). In 
“Add people or groups”, paste the service account’s email (from the JSON, it typically ends with 
iam.gserviceaccount.com). Set permissions to Editor (so it can write data). Send/Share. This is crucial – 
without it, the service account won’t see or modify the sheet . 

 
 
 
 
 
(If using OAuth credential, you don’t need to share, since it’s your own Google account with presumably 
access already. The OAuth is basically you, so it already has permission on your own sheets.) 
Now, in n8n, we’ll configure nodes to interact with Google Sheets: 
Set Up Google Sheets Node in n8n: 

1. 

In n8n Editor, open your “Stock Analysis Workflow” (create one if you haven’t). Add a 

Trigger node to start the workflow. For now, use a Cron (Schedule) Trigger. Search for “Cron” or 
“Schedule Trigger” and drag it in. We will configure it later to run at certain intervals (e.g., every X minutes 
or at specific times). To begin, you can leave it at default (which might be every hour or so) or set it to 
“Manual” trigger for testing. (There’s also a “Manual” trigger node for test runs – you can use that during 
development to run on click.) 

2. 
• 

Next, add a Google Sheets node. In the node’s properties: 
Select Credentials: choose either the OAuth credential or the Service Account credential 

you set up (e.g., “Google Sheets OAuth – yourname” or “Google Sheets Service Account”). If both are 
available, either will work now that the sheet is shared appropriately. 

• 

Action/Operation: Choose Read from spreadsheet or Get many rows (the exact 

wording depends on n8n version, but we want to retrieve data). For example, choose Operation: Read 
(to fetch rows). 
• 

Spreadsheet ID: paste the ID of your Google Sheet that you copied. (Alternatively, n8n 

might let you pick from a dropdown “Select a Spreadsheet” if your credential is OAuth and has drive 
access – in that case you might see the spreadsheet name. If you see it, you can select it from the list 
instead of pasting ID. With service account, listing may not work unless the service account has a Drive of 
its own or if using Google Drive API – easier just to paste ID.) 

• 

Sheet Name: type “Stocks” (or select from list if available). This tells the node which tab 

to read. We want to read the tickers. 

• 

Other options: n8n might have fields like “Range” or “Start Row”. If you leave them blank, 
it will default to all data in the sheet. Some versions allow leaving range empty to get all rows. If a range is 
required, you can specify something like “A:B” to cover both Ticker and Name columns. Or “A2:B100” to 
limit a range. To be safe, you can put “A:B” which means all rows and both columns A and B. 

• 

There may be an option for “Include headers” or “Use first row as header”. Enable that if 

available, so n8n uses the first row for field names. Then the output items will have JSON fields like Ticker 
and Company Name. 

• 

Once configured, execute this node (click the node and hit “Execute Node” while in 

manual mode). It should connect and fetch the data. You should see the output with one item per row 
(excluding header). For example, item 0 might be { "Ticker": "AAPL", "Company Name": "Apple Inc." }, 
item 1 for GOOGL, etc. If you see that, it means n8n successfully connected to your Google Sheet 
🎉. 

• 

Expected outcome: The Google Sheets node can read the “Stocks” sheet without 

errors. If successful, n8n displays the data in the node’s output. 

• 
• 

Troubleshooting: If you get an error: 
403 forbidden: likely service account not shared. Fix by sharing sheet (or if using OAuth, 

ensure you picked the right account). 

• 

404 not found: possibly wrong Spreadsheet ID or sheet name. Double-check the ID 

string and sheet tab name (case-sensitive). Also ensure the credential has access – a 404 can happen if 
the sheet isn’t accessible (Google returns not found for private sheets rather than forbidden in some 
cases). 

• 

No data: if it says success but output is empty, maybe the sheet was empty or the range 

was wrong (e.g., it might have assumed header row and returned nothing if no data under headers). 
Make sure you have some ticker rows under the header to test. Alternatively, in the node, disable “Only 

 
 
 
 
 
 
 
 
 
 
 
 
 
 
return data” or something to see raw output. Typically, populating a couple tickers as we did should yield 
output. 

3. 

Next, we’ll add nodes to use that list of tickers to fetch stock data from Alpha Vantage. 
Since n8n doesn’t have a built-in Alpha Vantage node, we will use an HTTP Request node to call the 
API. Add an HTTP Request node. Connect the Google Sheets node (Stocks) to this HTTP node. We 
want the HTTP node to execute for each ticker from the previous node. By default, n8n will run the HTTP 
node once per input item if we configure it properly (this is called looping through items). 

• 
• 

Set the HTTP node Method to GET. 
For URL, we need to construct the Alpha Vantage endpoint. We want perhaps the latest 

price or daily series. Alpha Vantage has an endpoint TIME_SERIES_DAILY that returns daily historical 
prices, and TIME_SERIES_INTRADAY for intraday. For simplicity, use daily or a specific “quote” endpoint. 
There is also a GLOBAL_QUOTE function that gives the latest price info. That might be simpler if we only 
want current data. For demonstration, let’s use GLOBAL_QUOTE (returns a small JSON with current 
price, volume, etc for one symbol). 

• 

The URL would look like: 

https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={{ $json["Ticker"] 
}}&apikey=YOUR_API_KEY. Here we’re using n8n’s expression syntax to insert the Ticker from the 
previous node’s JSON, and we will insert our API key. In n8n, you can click in the URL field, then toggle 
to Expression mode, and build the string. For example: 
= "https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=" + $json["Ticker"] + 
"&apikey=YOURKEY" 
Replace YOURKEY with your actual Alpha Vantage key (or better, reference a credential). 

• 

Security tip: It’s best not to paste the API key directly in the node, as it will be visible. 

Instead, consider storing it in n8n as an environment variable or in a separate credential. If n8n allowed, 
you could use the Credentials section of the HTTP node to set an API Key auth. However, Alpha 
Vantage expects the key as a query param, so using the credentials feature might not directly apply 
unless you use an OAuth2 cred (overkill here). A quick approach: store the key in a Workflow variable. 
For instance, use an SET node before the HTTP node that sets a field apiKey: 'YOURKEY', and then use 
$node["Set1"].json["apiKey"] in the URL. But for clarity, you might temporarily hardcode it and then 
remember to remove it or secure it later. (Since this guide is about best practices: ideally, use an 
environment variable: n8n allows you to reference process env via expressions like $env.KEY_NAME if 
configured, but on n8n.cloud you may not have access to set custom envs. So using a Set node or the 
credential is fine.) 
• 

For now, put the actual key in the URL after apikey=. We will not commit n8n workflows to 

a public repo, so it’s less of an issue, but still treat it carefully. 

• 
• 

No authentication needed in the HTTP node (we’re sending the key in URL). 
Under Options of HTTP node, enable “JSON/No error on fail” if available, or simply note 
that if one ticker fails, you might want the workflow to continue. (Alpha Vantage might return a JSON with 
an "Error Message" if something goes wrong or if limit exceeded.) 

• 

Now, execute the HTTP node. If the Google Sheets node had, say, 3 ticker items, the 
HTTP node will run 3 times (once per ticker). You should see output items corresponding to each. The 
output will be a JSON from Alpha Vantage. For GLOBAL_QUOTE, it looks like: 
{ 
  "Global Quote": { 
     "01. symbol": "AAPL", 
     "02. open": "170.00", 
     "03. high": "172.00", 
     "04. low": "169.50", 
     "05. price": "171.00", 

 
 
 
 
 
 
 
 
 
     "06. volume": "75000000", 
     "07. latest trading day": "2023-05-01", 
     "08. previous close": "169.50", 
     "09. change": "1.50", 
     "10. change percent": "0.885%" 
  } 
} 
All fields are strings. We will need to parse these out. The HTTP node may output this as {"Global Quote": 
{...}}. 

• 

If you got a valid response for each ticker, great. If you see an error like "Note": "Thank 

you for using Alpha Vantage! ... exceeding the standard call frequency" or similar, you might have hit the 
rate limit by firing them in parallel. n8n by default processes them sequentially (one after another) which 
should respect ~3 calls in a few seconds (that’s fine under 5/min). But if it were parallel, you might need to 
add a delay. We’ll assume sequential for now. If you did hit limit, try again but maybe only with 1-2 tickers, 
or consider using the Cron node to space them out (we will schedule the whole workflow anyway). 

• 

Troubleshooting HTTP step: If you got a network error, check internet connectivity from 
n8n (n8n cloud should have). If a “401” or some unauthorized, double-check the API key. If a “Invalid API 
call” message in the JSON, maybe the symbol is not recognized by Alpha Vantage (typo or an exotic 
symbol that needs a different API). Use common tickers for initial tests. 

4. 

Process the API Response: The Alpha Vantage data needs to be transformed to match 
our Google Sheets “Prices” format. We have fields like open, high, low, close, volume, etc., and we know 
the ticker and date. We need to extract those from the JSON. We can do this with an n8n Function node 
or Set node: 

• 

Add a Function (Item) node (this allows writing JavaScript to manipulate each item). 

Connect it after the HTTP node. 

• 

In the Function node code, you’ll have something like: 

// Each item is the JSON from HTTP, which has item.json["Global Quote"] 
const quote = item.json["Global Quote"]; 
// Create a new object with desired fields 
return { 
  json: { 
    Date: quote["07. latest trading day"], 
    Ticker: quote["01. symbol"], 
    Open: parseFloat( quote["02. open"] ), 
    High: parseFloat( quote["03. high"] ), 
    Low: parseFloat( quote["04. low"] ), 
    Close: parseFloat( quote["05. price"] ), 
    Volume: parseInt( quote["06. volume"], 10 ), 
    Indicator: parseFloat( quote["09. change"] )  // for example, we'll use absolute change as an "indicator" 
  } 
}; 
This converts the strings to numbers where appropriate (Open,High,…Volume) and picks the fields by 
their keys. We used change as an indicator (that is the absolute change from previous close). You might 
prefer something else; you could compute a simple indicator here too (like 10-day average if we had 
data). For now, this is fine. 

• 

If you’re not comfortable with JS, an alternative is using multiple Set nodes: one to 
extract each field via expressions. But that’s more cumbersome. The Function approach is concise. 

• 

Execute the Function node. The output should be items with json like: 

 
 
 
 
 
 
 
{ Date: "2023-05-01", Ticker: "AAPL", Open: 170, High: 172, Low: 169.5, Close: 171, Volume: 75000000, 
Indicator: 1.5 } for each stock (values will differ). 

• 

Confirm the data looks right and types are correct (n8n doesn’t require strict types, but 

when writing to Google Sheets, it will likely write numbers as plain values which is fine). 

5. 

Append to Google Sheets (Prices): Now take this formatted data and append it to the 

“Prices” sheet. Add another Google Sheets node after the Function node. 

• 
• 

Set Credentials (same Google Sheets cred). 
Operation: Append or Add Row (the exact wording might be “Append Sheet” or 

“Append Row”). We want to add new rows to the “Prices” sheet. 

• 
• 
• 

Specify Spreadsheet ID (paste the same ID or select from dropdown if available). 
Sheet Name: “Prices”. 
Now, map the fields. In n8n, when using Google Sheets Append, you often have to 

specify a Value to send for each column. Some versions let you toggle “Match columns by name”. If 
available, do that: it will match the JSON fields to columns with the same header name. This requires that 
your JSON keys exactly match the sheet headers. We made them match (“Date”, “Ticker”, etc.), so this 
should work. Enable “Use Header Row” or similar so that it knows to map by header . If this option isn’t 
present, you might have to manually specify the range or the values in order. 

• 

Alternatively, you can supply a range like “A:G” and provide an array of values. But 

mapping by header is easier to maintain. 

• 

Execute the Append node. If all goes well, it should add the data rows to the Google 

Sheet. Check your Google Sheet “Prices” tab – you should see new rows populated under the headers, 
one for each stock with the fetched values. 

• 

Expected outcome: The new stock data appears in the “Prices” sheet of your Google 

Spreadsheet. For example, AAPL’s row with today’s date and prices is now in the sheet. 

• 

Validation: Open the Google Sheet in your browser to confirm. Sometimes, there’s a 

slight delay, but usually it’s near-instant. If data is correct, you have successfully automated the data flow 
from API to Google Sheets via n8n. 

• 
• 

Troubleshooting Append: If the Google Sheets Append node gives an error: 
400 error about values: ensure the data format matches the sheet. If using header 

mapping, verify the headers exactly. If not using mapping, you may need to provide the exact range or 
fields. E.g., if it expects 7 columns and you give 7 values, it should align. 

• 

“Could not parse value”: maybe some type issue (less likely). Google Sheets might 

interpret a number as text if in quotes, but since we passed as number it should be fine. 

• 

No data added: Check that the Append node actually received input from previous node 
(each preceding item should pass through). In n8n, by default, multiple items from the Function will each 
pass to the Append node, and it will append each sequentially. If it only appended one, perhaps you need 
to enable “Append Google Sheets in Batch” or similar option. Some n8n versions have a toggle for 
appending all at once vs one-by-one. One-by-one is fine. 

• 

Service account permissions: If using service account and you forgot to share the 

sheet, you’ll get a 403. Fix by sharing (as described earlier). 

6. 

Fetching News & Sentiment: We have stock data being updated. Now for news. We 

can create a separate workflow, or extend this one. It might be wise to separate concerns: one workflow 
(or branch) for stock prices, another for news, so we can schedule them differently. But for simplicity, we’ll 
do it in one workflow with possibly a separate schedule or logic. 
Let’s extend the current workflow to fetch news for the tickers and analyze sentiment: 

• 

Add another HTTP Request node (or a branch from the original trigger) dedicated to 

NewsAPI. If continuing in one flow, you might use a Merge node or simply attach another branch from the 
Google Sheets (Stocks) node. In n8n, one node can have multiple outputs (the little dot at bottom can 

 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
connect to multiple next nodes). Connect the Stocks Google Sheets node also to this new HTTP node 
(so the tickers list feeds into both the stock data HTTP and news HTTP). 

• 

Configure this HTTP node to call NewsAPI’s /v2/everything endpoint. For example: 

https://newsapi.org/v2/everything?q={{ $json["Ticker"] 
}}&language=en&pageSize=3&apiKey=YOUR_NEWSAPI_KEY. Explanation: 

• 

q= is the query. We use the ticker as the query. This might or might not yield results; 
tickers like “AAPL” often appear in news about Apple, but some articles might not mention the ticker 
symbol. An alternative is to query the company name. We have the Company Name in $json as well 
(from the Stocks sheet). We could use that: e.g., q={{ $json["Company Name"] }}. That might fetch 
broader articles. Perhaps a combination (ticker OR name) is ideal but NewsAPI doesn’t support logical 
OR in a single query easily without multiple requests. For now, maybe use the company name to get 
more relevant results (assuming the name is distinct). 

• 
• 
• 
• 

language=en to filter English news. 
pageSize=3 to limit to 3 results per query (to not flood with too many). 
apiKey=YOURKEY with your NewsAPI key. 
Again, consider securing the key. For now, paste it. (Alternatively, you could store it in the 
same Set node or even use the same credentials concept – but n8n doesn’t have a NewsAPI integration, 
so manual is fine.) 
• 

This will fetch up to 3 articles for each ticker’s company. Execute it (maybe test with one 

ticker first by reducing input). 

• 

Check output: The NewsAPI returns JSON like: 

{ 
  "status": "ok", 
  "totalResults": 100, 
  "articles": [ 
    { 
      "source": { "id": "cnn", "name": "CNN" }, 
      "author": "...", 
      "title": "Apple launches new iPhone ...", 
      "description": "...", 
      "url": "...", 
      "publishedAt": "2023-05-01T12:34:56Z", 
      "content": "...." 
    }, 
    {... 2nd article ...}, 
    {... 3rd article ...} 
  ] 
} 
We care about title, source.name, publishedAt primarily for our sheet. We’ll ignore author/content for 
now, and do sentiment on the title (or description). 

• 

The HTTP node will output one item per input (per ticker) by default. But each item’s 

JSON will contain an array of articles. n8n will keep that as an array. To handle each article individually, 
we need to split that array into separate items. We can use a Split In Batches or a Function node to 
yield one item per article. A simpler method: use a Function node after the HTTP to explode the articles 
array. 

• 

Add a Function node after the News HTTP node with code like: 

const articles = item.json.articles || []; 
const ticker = $json["Ticker"];  // ticker from input (carried over) 
return articles.map(article => { 

 
 
 
 
 
 
 
 
 
 
  return { 
    json: { 
      Ticker: ticker, 
      Headline: article.title, 
      Source: article.source.name, 
      Date: article.publishedAt ? article.publishedAt.split('T')[0] : "", 
      FullText: article.description || "",  // we can use description for sentiment if title is short 
    } 
  } 
}); 
Here we produce multiple output items (one per article) each with Ticker, Headline, Source, Date (we cut 
the datetime to just date), and maybe FullText or Description to use for sentiment. (We include FullText 
just for sentiment analysis; not planning to write it to sheet except maybe we could but let’s not to keep 
sheet lighter.) 

• 

Now the function node should output multiple items (across all tickers). The next node will 

receive all news articles as separate items. 

• 

Sentiment Analysis: We don’t have a native n8n sentiment node. Options: call a 

sentiment API or run a small piece of code. Since n8n’s Function nodes run JavaScript (Node.js 
environment), we could code a simple sentiment analysis (like a naive one counting positive/negative 
words) or integrate with an external service. For simplicity, let’s do a naive approach: 

• 

Add another Function node (or extend the same one) to calculate sentiment. A very naive 

approach: use a simple algorithm or call a trivial API. To avoid complexity, we might choose to just tag 
sentiment as “Positive”, “Negative” or “Neutral” based on presence of certain words or a dummy 
approach. (Proper sentiment requires a library or an API like Azure Cognitive or Google NLP which is 
beyond scope/time.) 

• 

Alternatively, we perform sentiment in the Streamlit app (where we can use Python’s 

vaderSentiment or similar). That might actually be better for quality. Perhaps we skip calculating 
sentiment in n8n and instead just save the news, then have the Streamlit app compute sentiment on the 
fly or when displaying. However, the prompt said performing sentiment analysis as part of news 
integration – likely expecting some process here. 

• 

If we assume you want sentiment in the sheet (so it’s precomputed), an option: use AWS 

Comprehend or Google Cloud NL if you have keys, but that’s heavy. There is a free API called 
sentim-api (sentim-api.herokuapp.com) that might do basic sentiment. Or we use a pre-set dictionary in 
JS: e.g., check if title contains words like “up, gains, profit” vs “down, loss, crisis”. 

• 

For demonstration, let’s implement a very basic sentiment scoring in the Function: e.g., 

count positive words minus negative words in the headline + description. 

• 

Define small lists: 

const positiveWords = ["gain","upgrade","surge","positive","up","rise","beat","growth","profit"]; 
const negativeWords = ["fall","downgrade","drop","negative","down","decline","miss","loss","crisis"]; 
Then for each article text, do case-insensitive match count: 
let text = (article.title + " " + (article.description||"")).toLowerCase(); 
let score = 0; 
positiveWords.forEach(w => { if(text.includes(w)) score += 1; }); 
negativeWords.forEach(w => { if(text.includes(w)) score -= 1; }); 
let sentimentLabel = "Neutral"; 
if(score > 1) sentimentLabel = "Positive"; 
if(score < 0) sentimentLabel = "Negative"; 
(This is extremely simplistic and not linguistically robust, but enough to label some obvious cases.) 

• 

Attach this sentimentLabel to the item.json as Sentiment. 

 
 
 
 
 
 
 
 
• 

For clarity, you might do this in a separate node after splitting articles: one Function node 

to add Sentiment field to each item’s JSON. 

• 

After computing sentiment field, add a Google Sheets Append node for the “News” 

sheet, similar to what we did for Prices: 

• 
• 
• 
• 
• 

Credentials: Google Sheets cred 
Operation: Append Row 
Spreadsheet ID: (same ID) 
Sheet: News 
Map fields: ensure the JSON has Ticker, Headline, Source, Date, Sentiment keys 

matching the sheet headers. (We prepared it as such except we named Sentiment as sentimentLabel 
maybe, so adjust key to “Sentiment”). 

• 

Execute to append. Check the Google Sheet “News” tab to see if rows appeared with 

those values. 

• 

Expected outcome: The “News” sheet gets new rows for each fetched article, including 

the ticker, headline, source, date, and a sentiment label or score. 

• 

Troubleshooting News steps: If you get 0 articles (possible if no news for that query, or 

the ticker query didn’t match): 

• 

Try using company name in the query or a different endpoint. NewsAPI also has a 

“top-headlines” endpoint which can filter by query or category. But everything is fine for demonstration. 

active. 

• 

• 

If NewsAPI returns an error status, ensure the API key is correct and the account is 

If you hit the 100/day limit, you might need to wait or reduce frequency of news fetch. 

Perhaps fetch news less often than stock prices. 

• 

Sentiment logic is crude; don’t rely on it heavily. For better results, consider doing 

sentiment in Streamlit with a library like VADER (we’ll mention that soon). 
At this point, we have two data pipelines set up in n8n: 
Stock price updates to “Prices” sheet. 
News headlines (with naive sentiment) to “News” sheet. 

• 
• 

We should schedule them appropriately: 

• 

Scheduling workflows: The Cron trigger we added can be configured. For example, 

open the Cron node settings: 

• 

If you want stock prices updated throughout the day, you could set Every X minutes = 30 

(twice an hour) or a specific time each day after market close (if daily data). If using GLOBAL_QUOTE, 
you could do every hour during market hours. For simplicity, maybe set Cron to every day at e.g. 5:00pm 
(after market close) for final prices, and also every morning for pre-market open (if you want previous 
close data). 

• 

n8n’s Schedule Trigger can be set to multiple times. Or use separate Cron triggers in two 

workflows. 

• 

For news, maybe twice a day (morning and evening). You could either include it in the 

same workflow or have a separate workflow with its own trigger. It might be cleaner to separate (one 
workflow “Stock Prices update” scheduled more frequently, another “News update” scheduled less 
frequently). On n8n.cloud, you can have multiple workflows enabled. 

• 

For this guide, if we keep one workflow, you could still use conditional logic: e.g., in the 

workflow, use an IF node to check current time and decide to run news branch or not. But that’s 
advanced; easier is separate workflows. 
Set up workflow activation: 

• 

After testing everything manually (using manual trigger in editor and verifying outputs), 

you’ll deploy these workflows. On n8n.cloud, you need to Activate the workflow for it to run on schedule. 

 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
There’s usually a toggle or an “Activate” button. Activate the Price workflow (and News workflow if 
separate). Once active, n8n’s server will run the Cron triggers as configured. 
Validation: To confirm scheduling works, you might temporarily set Cron to a near time (like every 5 
minutes) and watch the executions in n8n’s “Executions” list. Ensure data is appending correctly and no 
errors occur. Then adjust to reasonable schedule. 
Common errors & tips for n8n workflows: 

• 

If an execution fails due to an API hiccup (like hitting limit or a network issue), you might 

want the workflow to continue for other tickers or retry later. n8n has options for error handling (like 
“Continue On Fail” on HTTP nodes, or wrap nodes in a Try/Catch). For production reliability, consider 
adding those. For example, set the Alpha Vantage HTTP node to not throw if one call fails – it could skip 
that ticker or use a catch to log it. 

• 

Logging: You might add a simple notification (like an email or a Slack message) if 

something critical fails (e.g., if no data fetched). This can be done via n8n’s email node or similar, but 
beyond scope here. 

• 

When scaling to many stocks or news articles, watch out for Google Sheets rate limits too 

(they allow quite a few writes per minute, but extremely rapid bursts might throttle). Our use is low 
volume, so should be fine. 
2.3 Retrieving Sheet ID & Data Organization (Best Practices & Scaling) 
We already retrieved the Spreadsheet ID and used it. As a reminder: the Spreadsheet ID is the unique 
identifier in the URL of the Google Sheet . Keep it noted because we’ll also need it in the Streamlit app. 
Alternatively, you can share the sheet with “Anyone with link can view” and use the sheet’s URL in some 
libraries, but since we have API access, we prefer using the ID with proper auth. 
Data Organization Recap: We have structured the data into three sheets. This separation is important: 
“Stocks” sheet is your configuration – easy for you or non-technical users to update the 
watchlist without touching code. If you add a ticker here, on the next n8n run it will automatically include it 
(assuming the workflow reads the whole list each time, which we did). 

• 

• 

“Prices” sheet is our time-series database of stock prices. Each row is a record of a 

stock’s price on a given date. This is essentially a fact table that can grow. If it becomes very large (say 
thousands of stocks over years), Google Sheets might get slow. That’s when you consider moving to 
PostgreSQL or another DB. 

• 

“News” sheet is a log of news items with sentiment. It too can grow, but you might 

periodically prune old news or limit to recent items if needed. For now, it’s fine. 
Scaling to PostgreSQL: 
Using Google Sheets is convenient for small scale and ease of use. But if your dataset or user base 
grows, a database is more robust: 

• 

When to switch: If you find the Google Sheet hitting performance issues (loading slowly 

for users, or API writes failing due to size), or if you need to do complex queries (like joining stocks with 
other data, filtering large history), a SQL database is better. Also, if you want multi-user robust access or 
to integrate with other tools, a DB is ideal. 

• 

Setting up Postgres: You could use a cloud database service (like Heroku Postgres, 

ElephantSQL, Amazon RDS, Google Cloud SQL, etc.). Provision a Postgres instance and note its 
connection details (host, port, database name, user, password). 

• 
• 
• 

Migrating data: You’d create tables corresponding to our sheets: 
A stocks table for tickers (maybe just ticker and name). 
A prices table with columns: date, ticker, open, high, low, close, volume, indicator 

(matching Google Sheet columns). The data types would be DATE, TEXT for ticker, numeric for prices, 
BIGINT for volume, numeric for indicator. 

• 

A news table with columns: ticker, headline, source, date (as date or datetime), sentiment 

(could be a numeric score or text label). 

 
 
 
 
 
 
 
 
 
 
 
 
• 

You can export data from Google Sheets as CSV and then import into Postgres to 

migrate historical data. 

• 

Using Postgres in n8n: n8n has a Postgres node. You would set up a new Credential in 
n8n for Postgres (providing the DB connection details). Then instead of Google Sheets nodes, you’d use 
Postgres nodes with SQL queries or inserts. For example, you’d replace the “Append Row” node with a 
“Postgres -> Insert” operation into the respective table. Or use parameterized queries. 

• 

Using Postgres in Streamlit: In the Streamlit app, instead of reading from the Google 

API, you’d connect using a library like psycopg2 or SQLAlchemy. You’d query the tables (e.g., SELECT * 
FROM prices WHERE ticker='AAPL') to get dataframes. This requires storing DB credentials in Streamlit 
secrets as well. 
• 

If you plan from the start to possibly scale, you can design your code to abstract the data 

layer. For now, we’ll proceed with Google Sheets, but just keep in mind these migration steps. 
Advantages of Google Sheets vs Postgres: 

• 

Sheets: easy to view and manually edit data, great for quick prototyping, non-developers 

can see the data live, no separate server needed. 

• 

Postgres: can handle more data, ACID transactions, better for integration with other 

systems, and structured querying. 
Best Practices Recap: 

• 

Keep configuration (tickers list) separate from generated data (prices, news). We did that 

with separate sheets. 

• 

Use clear headers and consistent naming so that automation can match fields easily (we 

matched keys to headers). 

• 

Regularly backup your Google Sheet (you can use “File -> Download as Excel/CSV” or 

set up an n8n workflow to back it up to Google Drive or send via email, etc.). This protects against 
accidental data loss if someone edits the sheet manually. 

• 

Monitor usage: Google API quotas for Sheets are generous (read/write requests per 

minute), but if you have hundreds of updates per minute, watch for any throttling messages in n8n logs. 
Now our data backend is all set. The Google Sheet is our central storage that the Streamlit app will use 
as its data source. 
Before moving to Streamlit coding, ensure n8n workflows are activated and running on schedule to keep 
data up-to-date. If you want on-demand updates (say a user triggers an analysis outside schedule), you 
could set up an n8n Webhook trigger that Streamlit could call to run the workflow immediately. That’s 
more advanced (the Streamlit app could do a POST request to n8n’s webhook, then wait a moment and 
fetch fresh data). If your use-case requires real-time on-demand updates, consider that pattern. For now, 
a reasonable schedule plus the ability to add new tickers which get picked up next cycle is often enough. 
We will now build the Streamlit dashboard that reads from this Google Sheet and presents the information 
to the user with appropriate visualization and interactivity. 
3. Setting Up Development Environment (Streamlit Dashboard) 
Finally, we create the Streamlit application that will serve as the user interface for our platform. The app 
will pull data from Google Sheets (using the API or a library), allow the user to select which stock to view, 
and display the latest prices and recent news with sentiment. We’ll also ensure our Python environment is 
properly configured with all needed libraries and that sensitive information (API keys, etc.) is handled 
securely. 
3.1 Installing Dependencies 
We need Python 3.9 or above for Streamlit (Streamlit supports 3.7+, but using 3.9+ is recommended for 
newer features). Verify your Python version: 
$ python --version 
Python 3.9.12 
If it’s lower, install Python 3.9 or 3.10 (e.g., via python.org or using pyenv). 

 
 
 
 
 
 
 
 
 
 
Create a Virtual Environment: It’s good to use a virtualenv to isolate packages. 
$ python -m venv venv  
$ source venv/bin/activate   # On Windows: venv\Scripts\activate 
Your shell prompt should indicate the env is active. 
Install required libraries: Based on our plan: 

• 
• 
• 
• 

Streamlit – the web framework. 
gspread (and google-auth) – to read Google Sheets easily via service account. 
pandas – for data manipulation and maybe plotting. 
requests – for any additional API calls (though we might not need since n8n is handling 

data fetch). 

• 

alpha_vantage (optional) – if we wanted to call Alpha Vantage directly in Streamlit for 

on-demand (but we offloaded that to n8n, so probably not needed in app). 

• 

newsapi-python (optional) – similarly, if we were to fetch news directly, but we did via 

n8n. We might not need it if we rely purely on the Sheets data. 

• 

vaderSentiment (or NLTK or textblob) – for a more robust sentiment analysis on the 

news if we want to recalc or verify sentiment in app. 

• 

plotly or matplotlib (optional) – Streamlit can plot using its native line_chart (which uses 
altair) or you can use Plotly. Streamlit’s st.line_chart is quick, so maybe we use that for stock price history. 
Let’s assume we’ll use Streamlit’s built-in chart for simplicity (no extra lib needed for plotting basic line 
chart). 
So minimal requirements: 
pip install streamlit pandas gspread google-auth vaderSentiment 
(vaderSentiment includes the lexicon; if not, we might need to download NLTK’s VADER lexicon, but pip 
install vaderSentiment typically is ready to use.) 
This installs the latest versions: 

• 
• 
• 
• 
• 

streamlit (let’s say 1.24.0 or above) 
pandas (e.g., 1.5.x) 
gspread (latest ~5.x) 
google-auth (as dependency of gspread for service account) 
vaderSentiment (3.3.2) 

Verify installation by importing in a Python REPL: 
import streamlit; import pandas; import gspread; import vaderSentiment 
No errors should mean all good. 
Update requirements.txt: Ensure these packages are listed in your repo’s requirements.txt with 
appropriate version pins (you can use pip freeze > requirements.txt, then edit out unnecessary ones, or 
manually write them). For example, your requirements.txt might contain: 
streamlit==1.24.0 
pandas==1.5.3 
gspread==5.7.2 
google-auth==2.17.3 
vaderSentiment==3.3.2 
(Version numbers are examples; using == pins exact versions. Alternatively use >= to allow minor 
updates. Pinning ensures consistency with Streamlit Cloud environment.) 
After editing, commit this file and push to GitHub. Streamlit Cloud will detect the change and reinstall 
deps. You can watch the logs to confirm it installed these packages. 
Local run test: You can also run the Streamlit app locally to test before pushing: 

• 

Create your app.py (or dashboard.py as named in deployment settings) and run streamlit 

run app.py. It should open in your browser (localhost:8501). 

• 

We’ll write the code in the next section. 

 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
3.2 Local n8n Setup for Testing Workflows (optional) 
(This item was in the outline, but since we have set up everything on n8n cloud, you might not need to run 
n8n locally. However, for completeness, here’s how you could.) 
If you wanted to develop n8n workflows on your machine: 

• 

Install n8n with npm (requires Node.js). For example: npm install -g n8n will install the 

CLI globally. 

cloud. 

• 

• 

Run n8n to start the editor on localhost:5678. It opens a web-based editor similar to the 

Be cautious to replicate credentials: for Google OAuth, the redirect URI would be different 

(perhaps http://localhost:5678/rest/oauth2-credential/callback for local). That’s complicated to set up; 
using service account is easier locally (no external callback needed). 

• 

You could export your cloud workflow (in n8n cloud editor, there’s an export option which 

gives JSON) and import into local n8n to test changes safely. 

• 

But since our workflows are working on n8n.cloud, this might not be necessary. It’s more 

relevant if you wanted to self-host n8n eventually or just practice offline. 
Security for local n8n: If running locally and exposing it (via tunneling or on a server), secure it with 
basic auth and HTTPS, as the n8n editor can control your workflows and credentials. 
Given we have done all config on n8n.cloud, you can skip local setup unless desired. 
3.3 Streamlit App Development (Organizing Project & Visualization) 
Now, we code the Streamlit dashboard. We’ll use the Google Sheets as the data source via the gspread 
library (using the service account JSON credentials). Alternatively, we could call Google’s REST API 
directly or use pandas.read_csv on a public CSV export link, but those are less secure or flexible. 
gspread with a service account is straightforward for reading and writing if needed. 
Setting up Google Sheets access in Streamlit: 

• 

We will use the service account JSON we created earlier. To use it in the app, we have 

two options: 

1. 

Use st.secrets mechanism: We can add the entire JSON content to the Streamlit 
secrets. Streamlit secrets can handle nested values (toml or JSON). We can paste the JSON in the 
secrets file (we have to ensure formatting is correct TOML). 

2. 

Use OAuth from Streamlit side: That would involve a different OAuth flow (complex for 

multiple users, not needed if we trust our app with the data). 
We’ll choose (1). In your .streamlit/secrets.toml (locally) or the Secrets section on Streamlit Cloud, add an 
entry like: 
[gcp_service_account] 
type = "service_account" 
project_id = "your-project-id" 
private_key_id = "abcdefg1234567..." 
private_key = "-----BEGIN PRIVATE KEY-----\nMIIEvQIBA...\n-----END PRIVATE KEY-----\n" 
client_email = "your-service-account@your-project.iam.gserviceaccount.com" 
client_id = "1234567890" 
auth_uri = "https://accounts.google.com/o/oauth2/auth" 
token_uri = "https://accounts.google.com/o/oauth2/token" 
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs" 
client_x509_cert_url = "...certificate url..." 
Basically, copy the entire JSON, and indent it under a section name (here [gcp_service_account]). Ensure 
newline characters in private_key are properly represented (\n as actual newlines or as \n in a TOML 
multiline string – the above should work since TOML will keep the literal \n as part of the value). Streamlit 
secrets is forgiving if you put it as one line with \n in string or as a literal multiline string. 
Also add other secrets: 

 
 
 
 
 
 
 
 
[secrets] 
ALPHAVANTAGE_KEY = "YOUR_ALPHA_VANTAGE_KEY" 
NEWSAPI_KEY = "YOUR_NEWSAPI_KEY" 
SHEET_ID = "YOUR_SPREADSHEET_ID" 
(Note: The [secrets] table in secrets.toml is actually not needed; you can put top-level keys directly. In 
Streamlit, everything in secrets.toml becomes st.secrets dictionary. So you could just do 
ALPHAVANTAGE_KEY = "..." at root. If using nested, like above gcp_service_account, it becomes 
st.secrets[“gcp_service_account”][“client_email”], etc.) 
Alternatively, you can structure secrets as: 
ALPHAVANTAGE_KEY = "..." 
NEWSAPI_KEY = "..." 
SHEET_ID = "..." 
[gcp_service_account] 
# ... (rest of JSON) 
This way, st.secrets["ALPHAVANTAGE_KEY"] gives the key, and st.secrets["gcp_service_account"] gives 
the nested credentials dict. 
Upload these secrets to Streamlit Cloud (through the web UI: Settings -> Secrets, paste the content). 
Locally, create a .streamlit/secrets.toml file with the same content so that st.secrets works in local testing 
too . 
Now we write app.py: 
Pseudo-code for Streamlit app: 
import streamlit as st 
import pandas as pd 
import gspread 
from google.oauth2.service_account import Credentials 
from datetime import datetime, timedelta 
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer 
# Page config (optional) 
st.set_page_config(page_title="Stock Analysis Dashboard", layout="wide") 
st.title("📊 Automated Stock Analysis Dashboard") 
# Authenticate with Google Sheets 
# Get creds from secrets 
if "gcp_service_account" in st.secrets: 
    sa_info = st.secrets["gcp_service_account"] 
    creds = Credentials.from_service_account_info(sa_info, scopes=[ 
        "https://www.googleapis.com/auth/spreadsheets", 
        "https://www.googleapis.com/auth/drive" 
    ]) 
    client = gspread.authorize(creds) 
else: 
    st.error("Service account credentials not found in secrets.") 
    st.stop() 
# Open the spreadsheet by ID 
SHEET_ID = st.secrets["SHEET_ID"] 
try: 
    sh = client.open_by_key(SHEET_ID) 
except Exception as e: 
    st.error("Failed to open Google Sheet. Check permissions and ID.") 
    st.stop() 

# Read the Stocks sheet to get list of tickers and names 
try: 
    stocks_ws = sh.worksheet("Stocks") 
    stocks_data = stocks_ws.get_all_records()  # returns list of dicts for each row (using header row as 
keys) 
except Exception as e: 
    st.error("Failed to read 'Stocks' worksheet.") 
    st.stop() 
if not stocks_data: 
    st.warning("No stocks found in configuration sheet.") 
    st.stop() 
# Create DataFrame of stocks for easy filtering 
stocks_df = pd.DataFrame(stocks_data) 
# Ensure 'Ticker' column exists (get_all_records uses headers as keys directly) 
if "Ticker" not in stocks_df.columns: 
    st.error("Stocks sheet is missing 'Ticker' column.") 
    st.stop() 
# Sidebar: select a ticker (or multiple) 
tickers = stocks_df["Ticker"].tolist() 
selected_ticker = st.sidebar.selectbox("Select a stock to analyze:", options=tickers) 
company_name = stocks_df[stocks_df["Ticker"] == selected_ticker]["Company Name"].values 
company_name = company_name[0] if len(company_name) > 0 else "" 
# Sidebar: Option to trigger on-demand update (if we had a webhook or direct API call) 
# For now, just a placeholder button 
if st.sidebar.button("Refresh Data Now"): 
    st.info("Data refresh triggered (placeholder).") 
st.subheader(f"Stock Price History – {selected_ticker} {company_name}") 
# Read Prices sheet data for the selected ticker 
prices_ws = sh.worksheet("Prices") 
# We can fetch all and filter, or use query. gspread doesn't support query, so get all into a DataFrame 
prices_data = prices_ws.get_all_records() 
prices_df = pd.DataFrame(prices_data) 
if not prices_df.empty: 
    # Convert Date column to datetime 
    if "Date" in prices_df.columns: 
        prices_df["Date"] = pd.to_datetime(prices_df["Date"], errors='coerce') 
    # Filter for the selected ticker 
    ticker_df = prices_df[prices_df["Ticker"] == selected_ticker].copy() 
    if ticker_df.empty: 
        st.write("No price data for this ticker yet.") 
    else: 
        ticker_df.sort_values("Date", inplace=True) 
        # Show latest price and change 
        latest = ticker_df.iloc[-1] 
        prev = ticker_df.iloc[-2] if len(ticker_df) > 1 else None 
        latest_price = latest["Close"] 
        st.metric(label=f"Latest Close Price ({latest['Date'].date()})", value=f"${latest_price:.2f}", 
                  delta=(f"{(latest['Indicator']):+.2f}" if 'Indicator' in latest else None)) 
        # Plot price history 

        st.line_chart(ticker_df.set_index("Date")["Close"]) 
        # Optionally, display a table of recent data 
        st.dataframe(ticker_df.tail(5).reset_index(drop=True)) 
else: 
    st.write("Price data sheet is empty.") 
# News section 
st.subheader(f"Recent News for {selected_ticker}") 
news_ws = sh.worksheet("News") 
news_data = news_ws.get_all_records() 
news_df = pd.DataFrame(news_data) 
if not news_df.empty: 
    # Filter for ticker 
    news_df_ticker = news_df[news_df["Ticker"] == selected_ticker].copy() 
    # Sort by date (assuming Date is a string YYYY-MM-DD or similar) 
    news_df_ticker["Date"] = pd.to_datetime(news_df_ticker["Date"], errors='coerce') 
    news_df_ticker.sort_values("Date", ascending=False, inplace=True) 
    # If sentiment not in data or we want to recalc with VADER: 
    sia = SentimentIntensityAnalyzer() 
    def calc_sentiment(text): 
        return sia.polarity_scores(text)["compound"] 
    if "Sentiment" not in news_df_ticker.columns: 
        # Calculate sentiment if not present 
        news_df_ticker["SentimentScore"] = news_df_ticker["Headline"].fillna("").apply(calc_sentiment) 
        news_df_ticker["Sentiment"] = news_df_ticker["SentimentScore"].apply(lambda s: "Positive" if s > 0.2 
else ("Negative" if s < -0.2 else "Neutral")) 
    # Display the latest few news 
    for _, row in news_df_ticker.head(5).iterrows(): 
        sent = row.get("Sentiment", "N/A") 
        head = row["Headline"] 
        source = row.get("Source", "") 
        date_str = row["Date"].strftime("%Y-%m-%d") if pd.notnull(row["Date"]) else str(row["Date"]) 
        # Use colored emojis or icons for sentiment 
        icon = "🔼" if sent == "Positive" else ("🔽" if sent == "Negative" else "➡") 
        st.write(f"- {icon} **{head}** *({source}, {date_str})* – Sentiment: **{sent}**") 
    # Optionally, allow expanding to see all news 
    if st.checkbox("Show all news data"): 
        st.dataframe(news_df_ticker.reset_index(drop=True)) 
else: 
    st.write("No news data available for this ticker.") 
Let’s break down what this app does: 

• 

Google Sheets access: It uses the service account credentials from st.secrets to 

authorize via gspread. We set the scopes to read/write Sheets and Drive. We open the spreadsheet by 
ID. This requires that the service account email is shared on the sheet (which we did in Section 2). If 
something is wrong (sheet not shared or ID incorrect), we handle the exception and stop. 

• 

Load configuration (Stocks list): We fetch all records from “Stocks” sheet. This returns 

a list of dictionaries thanks to gspread’s get_all_records(), where the keys are the header names. We 
convert to DataFrame for ease of filtering. We present a selectbox in the sidebar for the user to choose 
one of the tickers. (We default to the first ticker or none if empty.) 

 
 
• 

Trigger refresh button: We placed a refresh button in the sidebar. Currently, it doesn’t 

actually call n8n’s webhook or anything – it’s just a placeholder printing a message. If we wanted, we 
could integrate this with a webhook: e.g., if clicking refresh, use requests.post(n8n_webhook_url) to 
trigger the workflow, then maybe re-read the sheets. However, n8n execution might not be instantaneous 
or might take a few seconds, so one approach is to call webhook, then poll for updated data or force a 
reload after a delay. Given complexity, we just note it. In a real scenario, you can implement this if 
needed. 
• 

Display stock price history: We read the entire “Prices” sheet into a DataFrame (could 
be large; if performance suffers, we could modify the approach by querying only needed data, but Google 
Sheets API doesn’t support query natively, you’d have to filter in Python or use Google’s query language 
via a different approach). For now, reading all and filtering is fine for moderate data sizes. We filter the 
DataFrame for the selected ticker. We sort by date. We then display: 

• 

A metric (big number) showing the latest close price and the change. We use the 

“Indicator” as we stored which was the change amount (or you could compute percent change between 
last two closes). 
• 

A line chart of the Close price over time. We use st.line_chart on the DataFrame’s Close 

column indexed by Date. Streamlit will automatically render a line graph. 

• 

A dataframe showing the last 5 records as a quick table (so user can see recent values). 

Streamlit’s st.line_chart is a high-level API; under the hood it uses Altair or Vega. It’s fine for simple 
series. If we wanted more control (like multiple series, custom axis), we could use Altair or Plotly. But to 
keep it simple, this works. 

• 

Display recent news and sentiment: We read the “News” sheet completely and filter for 

the selected ticker. Sort by date (newest first). We then ensure we have sentiment: 

• 

If our sheet already had a “Sentiment” column from n8n (like “Positive” etc.), we can use 

it. If we also have a “SentimentScore” or want a more precise measure, we could recalc or use it. 

• 

In the code, I assumed maybe the sheet has only the label. If it doesn’t have any, we 

calculate compound sentiment using VADER (SentimentIntensityAnalyzer) on the headline. VADER gives 
a compound score between -1 and 1. We then label it positive/negative/neutral based on thresholds 
(commonly >0.05 positive, < -0.05 negative, else neutral — I used 0.2 for a bit stronger signal). 

• 

We display up to 5 latest news items as bullet points with the headline, source, date, and 

sentiment. We prepend an icon (🔼 green/up arrow for positive, 🔽 red/down arrow for negative, etc. 
Actually I used unicode arrows without color). 

• 

We also allow a checkbox to show the full news data (for debugging or if user wants to 

scroll more). 

• 

UI considerations: We used st.set_page_config to set a title and wide layout (so it uses 

full width, which is nice for data tables). 

• 

We used emojis in the title and bullet points for a bit of visual flair. 

Testing Locally: Run streamlit run app.py with your local secrets file in place. It should open and show 
the dashboard. Try selecting different tickers. If no data, maybe you need to run n8n to populate or adjust 
the code if expecting different columns. 
Common issues in Streamlit app: 

• 

Google Sheets read performance: get_all_records() fetches everything. If the sheet 

has thousands of rows, this could be a bit slow (a few seconds). Streamlit will run these every app 
interaction unless we cache them. We could use st.cache_data to cache the sheet reads for, say, a 
minute or two so that moving the slider or interacting doesn’t re-fetch constantly. Consider adding: 
@st.cache_data(ttl=60) 
def load_sheet(ws): 
    return ws.get_all_records() 
prices_data = load_sheet(prices_ws) 

 
 
 
 
 
 
 
 
 
 
 
 
 
This will cache the result for 60 seconds. 

• 

Session State: We aren’t using any, but if we had a refresh button calling webhook 

asynchronously, we might use st.session_state to handle a loading state. 

• 

Service Account JSON size: Putting the entire JSON in secrets is fine, but note it 

counts towards Streamlit’s secret size limits (I think 100KB total). The JSON is usually 2KB, so no 
problem. 
• 

Pandas vs gspread for partial reads: gspread doesn’t easily allow filtering on the 

Google side. Another approach could be using Google Sheets API via googleapiclient.discovery to query 
specific ranges (like 'Prices'!A:F for only certain columns or using a query with Google Visualization API – 
but that’s complex). Given moderate data, the current approach is acceptable. 
Security in Streamlit app: 

• 

Our Streamlit app uses the service account with edit access to the sheet. If the app is 
public, technically a malicious user could craft requests to use gspread to edit the sheet (since our app 
code has the credentials and full access). We didn’t provide any UI to edit, but the gspread client is there. 

• 

To mitigate, you could set the service account permission to Viewer on the sheet (so it 
can read but not write). However, get_all_records might require at least read which is fine. If we’re not 
writing from Streamlit, view is enough. But the service account JSON itself has edit scope we gave 
(drive.file). 

• 

Alternatively, we could share the sheet as read-only public and use an API key to fetch as 

CSV. But that exposes data publicly. 

• 

As this is a dashboard and not meant for user edits, it’s okay. Just be mindful that if 

someone gained access to your Streamlit st.secrets (which only the app backend has), they could misuse 
the credentials. Streamlit Cloud ensures secrets aren’t exposed to the browser or other users, so that’s 
safe as long as your code doesn’t accidentally print them. 

• 

API keys (Alpha Vantage, NewsAPI) are in st.secrets but we didn’t actually use them in 

the Streamlit code (because we relied on n8n to fetch data). You might still keep them in secrets if you 
plan to allow direct API calls from Streamlit (like on-demand refresh bypassing n8n). If not needed, you 
could omit them. No harm keeping them hidden though. 
3.4 Configuration Files & Security (Environment Variables, .env, .gitignore) 
We already used secrets.toml which is Streamlit’s way of managing environment variables securely on 
deployment  . Some additional points: 

• 

.env for local dev: If you weren’t using Streamlit’s secrets, another approach is a .env 
file and using python-dotenv to load it. For example, put keys in .env and call load_dotenv(). However, 
since Streamlit has a built-in solution, we used that to avoid another dependency. Just ensure .env and 
secrets.toml are in .gitignore so you don’t commit keys. 

• 

GitHub Repo Security: Double-check that you did not accidentally commit the service 
account JSON or any keys. The .gitignore should include *.json if you had the service key as a file, and 
.streamlit/ if you store secrets there locally. It’s easy to slip, so review your commits on GitHub for any 
secrets. If found, invalidate those keys immediately. 

• 

API Keys in n8n: In n8n.cloud, the credentials (like the Google OAuth, service account, 
etc.) are encrypted in their database. The Alpha Vantage key we put in the HTTP node URL is somewhat 
visible in the workflow. If you share the workflow JSON or invite others to n8n, that key could be seen. 
Better practice: store it in an n8n credential: 

• 

n8n has a credential type “API Key” for some services or you can use an environment 

variable. On n8n.cloud, you might set the key as an environment variable via their interface (if supported). 
Or create a separate workflow with the key that only yields the key, but that’s overkill. 

• 

At minimum, if you are the only one using n8n, having it in the workflow is okay. But treat 

the workflow JSON as sensitive. If you export it, remove the key before sharing. 

 
 
 
 
 
 
 
 
 
 
 
 
 
• 

Rotate keys if needed: For long-term security, periodically rotate API keys (generate 

new ones and update secrets). For example, if someone accidentally logged an API response that 
contained the key (some APIs echo your key), rotating ensures any exposure is short-lived. 

• 

OAuth client secret safety: The Google OAuth client secret is stored in n8n credential. 

That’s secure in n8n. We did not expose it elsewhere. Good. 

• 

Service account key safety: We put it in Streamlit secrets (encrypted at rest on 

Streamlit Cloud) . That’s fine. Just don’t print it or something. If the app had an error and printed the entire 
st.secrets, that would be a huge leak. We carefully pick only needed fields from secrets. 

• 

Streamlit app access control: If this app is for personal use or a small group, you may 
not want it publicly accessible by anyone. Streamlit Community Cloud allows you to set sharing settings. 
You can go to the app’s settings on Streamlit Cloud and under “Authorization” add specific email 
addresses who can access, or require login. If left open, be comfortable that the data shown isn’t super 
sensitive or that you don’t mind if someone stumbles on it. Since it’s mostly stock info (which is public) 
and some analysis, it’s not a big deal if someone else saw it. But generally, restrict to your use if not 
intended for the public. 

• 

Memory and efficiency: Using st.cache_data (with ttl or max_entries) for Google Sheets 

data can help performance and avoid hitting Google API quotas from the app side. e.g., If 10 users are 
viewing the app, each might trigger data fetch. Caching will ensure they reuse the same data instead of 
hitting Google 10 times. We might add: 
@st.cache_data(ttl=300) 
def load_prices(): 
    return pd.DataFrame(prices_ws.get_all_records()) 
prices_df = load_prices() 
and similarly for news. 5 minutes TTL is fine if data updates every hour or daily. Adjust based on how 
fresh you need it. Because if n8n updates sheet at 5:00pm and someone is viewing at 5:01pm, you want 
them to see new data, so maybe small TTL or provide a refresh button that clears cache (Streamlit’s 
cache can be cleared via an explicit call or just skip caching on manual refresh). 

• 

Local vs Cloud differences: On Streamlit Cloud, st.secrets is fully supported. Locally, it 

reads from .streamlit/secrets.toml. Ensure you have that file when running locally or adjust to load from 
environment variables if not found. Our code doesn’t handle missing st.secrets well besides the service 
account check. Perhaps add: 
if "SHEET_ID" not in st.secrets: 
    # fallback to env var if running outside Streamlit Cloud 
    import os 
    SHEET_ID = os.getenv("SHEET_ID") 
    # similarly for other keys... 
But since we plan to run in Streamlit Cloud primarily, it’s okay. 
Final Thoughts and Next Steps: 
We have put together a detailed setup covering accounts, configuration, development, and security. After 
following this guide, you should have: 

• 

An n8n.cloud workflow that regularly fetches stock prices from Alpha Vantage and news 

from NewsAPI (with sentiment tagging), updating a Google Sheet. 

• 

A Google Sheet acting as both the control center (tickers list) and the database (storing 

historical data and news). 

• 

A Streamlit dashboard that reads from the Google Sheet and presents interactive 

visualizations and metrics for the stocks, along with recent news sentiment. 

• 

Secure handling of credentials using service accounts and secrets management, with no 

sensitive info in code or git. 
This setup is robust for a small-scale application. As you use it, you may consider enhancements: 

 
 
 
 
 
 
 
 
 
 
• 

Adding more technical indicators (perhaps calculate moving averages or RSI in the n8n 

workflow using Alpha Vantage’s technical indicators endpoint or compute in Python). 

• 

Incorporating more news sources or a more sophisticated sentiment analysis (maybe 

using a machine learning model via an API or library). 

• 
• 

Scaling the data backend to a SQL database if the Google Sheet becomes a bottleneck. 
Implementing the on-demand refresh in Streamlit by calling n8n’s webhook (which could 

run the workflow immediately for a given ticker and update the sheet/app in near-real-time). 

• 

Adding user authentication to Streamlit (if multiple people use it, you could have them 
login via email and perhaps have each user’s watchlist; though that complicates the data separation – 
might need separate sheets per user, etc.). 
With the foundations laid out in this guide, you can confidently expand or modify the platform to suit your 
needs, knowing that you followed best practices for deployment and security along the way. Happy 
automating!
