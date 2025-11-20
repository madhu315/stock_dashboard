from django.shortcuts import render
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.offline as opy

AVAILABLE_INDICATORS = ['SMA', 'EMA']

# Mapping for user-friendly period selection
PERIOD_MAP = {
    '1d': '1d', '1w': '7d', '1mo': '1mo', '3mo': '3mo', '6mo': '6mo',
    '1y': '1y', '3y': '3y', '5y': '5y', 'all': 'max'
}


def stock_dashboard(request):
    stock = request.GET.get('stock', 'TCS.NS')
    timeframe = request.GET.get('timeframe', 'daily')
    selected_period = request.GET.get('period', '6mo')
    selected_indicators = request.GET.getlist('indicator')

    # Map timeframe to interval
    interval_map = {'daily': '1d', 'weekly': '1wk', 'monthly': '1mo'}
    interval = interval_map.get(timeframe, '1d')

    # Map selected period to yfinance
    yf_period = PERIOD_MAP.get(selected_period, '6mo')

    # ------------------📌 Download data (NO SESSION OVERRIDE) ------------------
    try:
        df = yf.download(
            tickers=stock,
            period=yf_period,
            interval=interval,
            auto_adjust=True,
            progress=False
        )

        if df.empty:
            return render(request, 'dashboard.html', {
                'graph': None,
                'error': f"No data found for {stock}.",
                'indicators': AVAILABLE_INDICATORS,
                'stock': stock,
                'timeframe': timeframe,
                'selected_indicators': selected_indicators,
                'selected_period': selected_period,
                'periods': PERIOD_MAP.keys()
            })

    except Exception as e:
        return render(request, 'dashboard.html', {
            'graph': None,
            'error': str(e),
            'indicators': AVAILABLE_INDICATORS,
            'stock': stock,
            'timeframe': timeframe,
            'selected_indicators': selected_indicators,
            'selected_period': selected_period,
            'periods': PERIOD_MAP.keys()
        })

    # ------------------📌 Reset Index & Ensure Date column ------------------
    df = df.reset_index()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [' '.join([str(i) for i in col]).strip() for col in df.columns]

    if df.columns[0].lower() not in ['date', 'datetime']:
        df.rename(columns={df.columns[0]: 'Date'}, inplace=True)

    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date').reset_index(drop=True)

    # ------------------📌 Determine price column ------------------
    if 'Close' in df.columns:
        price_col = 'Close'
    else:
        price_col = df.select_dtypes(include='number').columns[0]
        df['Close'] = df[price_col]

    # ------------------📌 Add Indicators ------------------
    if len(df) >= 20:
        if 'SMA' in selected_indicators:
            df['SMA_20'] = df['Close'].rolling(window=20).mean()

        if 'EMA' in selected_indicators:
            df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
    else:
        df['SMA_20'] = None
        df['EMA_20'] = None

    # ------------------📌 Prepare Data for Plot ------------------
    indicator_cols = ['Close']
    if 'SMA_20' in df:
        indicator_cols.append('SMA_20')
    if 'EMA_20' in df:
        indicator_cols.append('EMA_20')

    plot_df = df[['Date'] + indicator_cols].melt(
        id_vars='Date',
        var_name='Indicator',
        value_name='Price'
    )

    # ------------------📌 Create Plotly Chart ------------------
    fig = px.line(
        plot_df,
        x='Date',
        y='Price',
        color='Indicator',
        title=f'{stock} Price & Indicators ({timeframe.capitalize()}, {selected_period})',
        template='plotly_white'
    )
    fig.update_layout(height=600)

    graph_div = opy.plot(
        fig,
        auto_open=False,
        output_type='div',
        config={'displayModeBar': True}
    )

    # ------------------📌 Render Template ------------------
    return render(request, 'dashboard.html', {
        'graph': graph_div,
        'stock': stock,
        'timeframe': timeframe,
        'periods': PERIOD_MAP.keys(),
        'selected_period': selected_period,
        'indicators': AVAILABLE_INDICATORS,
        'selected_indicators': selected_indicators,
        'error': None
    })
