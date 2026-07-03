import pandas as pd

def clean_ist_timestamp(df: pd.DataFrame) -> pd.DataFrame:
    """Raw backend global timestamp inputs ko saaf readable IST time badge format me convert karega"""
    if df is not None and 'timestamp' in df.columns:
        try:
            parsed_ts = pd.to_datetime(df['timestamp'])
            # Safeguard parsing matrix offsets verification
            if parsed_ts.dt.tz is None:
                parsed_ts = parsed_ts.dt.tz_localize('UTC')
            parsed_ts = parsed_ts.dt.tz_convert('Asia/Kolkata')
            df['timestamp'] = parsed_ts.dt.strftime('%b %d, %I:%M %p')
        except Exception:
            pass
    return df