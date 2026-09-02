import os

import logging

import numpy as np

import pandas as pd

import yfinance as yf

from telegram import Update

from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(

    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",

    level=logging.INFO,

)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

SYMBOL = "GC=F"

INTERVAL = "15m"

PERIOD = "5d"

def ema(series, span):

    return series.ewm(span=span, adjust=False).mean()

def rsi(series, period=14):

    delta = series.diff()

    gain = delta.clip(lower=0)

    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()

    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)

    return 100 - (100 / (1 + rs))

def atr(df, period=14):

    prev_close = df["Close"].shift(1)

    tr = pd.concat(

        [

            df["High"] - df["Low"],

            (df["High"] - prev_close).abs(),

            (df["Low"] - prev_close).abs(),

        ],

        axis=1,

    ).max(axis=1)

    return tr.ewm(alpha=1 / period, adjust=False).mean()

def get_gold_data():

    df = yf.download(

        SYMBOL,

        period=PERIOD,

        interval=INTERVAL,

        progress=False,

        auto_adjust=False,

    )

    if isinstance(df.columns, pd.MultiIndex):

        df.columns = df.columns.get_level_values(0)

    df = df.dropna()

    return df

def analyze_gold():

    df = get_gold_data()

    df["EMA20"] = ema(df["Close"], 20)

    df["EMA50"] = ema(df["Close"], 50)

    df["RSI"] = rsi(df["Close"])

    df["MACD"] = ema(df["Close"], 12) - ema(df["Close"], 26)

    df["MACD_SIGNAL"] = ema(df["MACD"], 9)

    df["ATR"] = atr(df)

    last = df.iloc[-1]

    price = float(last["Close"])

    rsi_value = float(last["RSI"])

    atr_value = float(last["ATR"])

    buy_score = 0

    sell_score = 0

    if last["EMA20"] > last["EMA50"]:

        buy_score += 2

    else:

        sell_score += 2

    if price > last["EMA20"]:

        buy_score += 1

    else:

        sell_score += 1

    if last["MACD"] > last["MACD_SIGNAL"]:

        buy_score += 2

    else:

        sell_score += 2

    if 52 <= rsi_value <= 68:

        buy_score += 2

    elif 32 <= rsi_value <= 48:

        sell_score += 2

    if buy_score >= 5 and buy_score > sell_score:

        signal = "BUY"

        sl = price - atr_value * 1.2

        risk = price - sl

        tp1 = price + risk * 1.5

        tp2 = price + risk * 2.5

        icon = "🟢"

    elif sell_score >= 5 and sell_score > buy_score:

        signal = "SELL"

        sl = price + atr_value * 1.2

        risk = sl - price

        tp1 = price - risk * 1.5

        tp2 = price - risk * 2.5

        icon = "🔴"

    else:

        signal = "WAIT"

        sl = None

        tp1 = None

        tp2 = None

        icon = "🟡"

    text = (

        f"{icon} Gold Signal Pro\n\n"

        f"XAU/USD Analysis\n"

        f"Signal: {signal}\n\n"

        f"Price: {price:.2f}\n"

        f"RSI: {rsi_value:.1f}\n"

        f"BUY Score: {buy_score}\n"

        f"SELL Score: {sell_score}\n"

    )

    if signal != "WAIT":

        text += (

            f"\nEntry: {price:.2f}\n"

            f"Stop Loss: {sl:.2f}\n"

            f"TP1: {tp1:.2f}\n"

            f"TP2: {tp2:.2f}\n"

        )

    text += (

        "\n⚠️ التحليل للتداول التجريبي وإدارة المخاطر."

        "\nلا توجد إشارة مضمونة 100%."

    )

    return text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(

        "🥇 Gold Signal Pro جاهز\n\n"

        "اضغط /gold لتحليل الذهب الآن."

    )

async def gold(update: Update, context: ContextTypes.DEFAULT_TYPE):

    msg = await update.message.reply_text(

        "⏳ جاري تحليل الذهب..."

    )

    try:

        result = analyze_gold()

        await msg.edit_text(result)

    except Exception as e:

        await msg.edit_text(

            f"حدث خطأ أثناء التحليل:\n{e}"

        )

def main():

    if not TOKEN:

        raise RuntimeError(

            "TELEGRAM_BOT_TOKEN غير موجود"

        )

    app = Application.builder().token(TOKEN).build()

    app.add_handler(

        CommandHandler("start", start)

    )

    app.add_handler(

        CommandHandler("gold", gold)

    )

    app.run_polling(

        drop_pending_updates=True

    )

if __name__ == "__main__":

    main()
