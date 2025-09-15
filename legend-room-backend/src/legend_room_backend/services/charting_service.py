import os
import yfinance as yf
import plotly.graph_objects as go
import tempfile
import cloudinary
import cloudinary.uploader
import requests

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)

SCREENSHOT_SERVICE_URL = os.getenv("SCREENSHOT_SERVICE_URL")


def generate_chart(ticker: str) -> str:
    try:
        df = yf.download(ticker, period="6mo", interval="1d", auto_adjust=True)
        if df.empty or len(df) < 30:
            raise Exception("Insufficient data")

        df["21EMA"] = df["Close"].ewm(span=21).mean()
        df["50SMA"] = df["Close"].rolling(window=50).mean()
        df["200SMA"] = df["Close"].rolling(window=200).mean()

        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="Candles"
        ))
        fig.add_trace(go.Scatter(x=df.index, y=df["21EMA"], line=dict(color="blue"), name="21 EMA"))
        fig.add_trace(go.Scatter(x=df.index, y=df["50SMA"], line=dict(color="red"), name="50 SMA"))
        fig.add_trace(go.Scatter(x=df.index, y=df["200SMA"], line=dict(color="orange"), name="200 SMA"))

        fig.update_layout(
            title=ticker,
            template="plotly_dark",
            xaxis_rangeslider_visible=False,
            height=600
        )

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            fig.write_image(tmp.name)
            upload_result = cloudinary.uploader.upload(tmp.name, folder="legend-room", public_id=f"{ticker}_chart", overwrite=True)
            return upload_result["secure_url"]

    except Exception:
        # Fallback to TradingView screenshot engine or generic dummy
        try:
            fallback_url = f"{SCREENSHOT_SERVICE_URL}/screenshot?symbol={ticker}"
            r = requests.get(fallback_url, timeout=30)
            r.raise_for_status()
            data = r.json()
            return data.get("chart_url")
        except Exception:
            return f"https://dummyimage.com/1200x750/131722/ffffff&text={ticker}+Chart"
