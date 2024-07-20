import MetaTrader5 as mt5
import pandas as pd
import time
from datetime import datetime

class MT5TradingAlgorithm:
    def __init__(self, symbol, lot_size, max_risk_percent=2, max_open_positions=3):
        self.symbol = symbol
        self.lot_size = lot_size
        self.max_risk_percent = max_risk_percent
        self.max_open_positions = max_open_positions
        
        # Initialize connection to MT5
        if not mt5.initialize():
            print("initialize() failed")
            mt5.shutdown()

    def fetch_data(self, timeframe, num_candles):
        rates = mt5.copy_rates_from_pos(self.symbol, timeframe, 0, num_candles)
        return pd.DataFrame(rates)

    def analyze_data(self, df):
        df['SMA_20'] = df['close'].rolling(window=20).mean()
        df['SMA_50'] = df['close'].rolling(window=50).mean()
        
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        return df

    def generate_signal(self, df):
        if df['SMA_20'].iloc[-1] > df['SMA_50'].iloc[-1] and df['RSI'].iloc[-1] < 30:
            return 'BUY'
        elif df['SMA_20'].iloc[-1] < df['SMA_50'].iloc[-1] and df['RSI'].iloc[-1] > 70:
            return 'SELL'
        else:
            return 'HOLD'

    def calculate_position_size(self):
        account_info = mt5.account_info()
        if account_info is None:
            raise ValueError("Failed to get account info")

        balance = account_info.balance
        risk_amount = balance * (self.max_risk_percent / 100)
        
        symbol_info = mt5.symbol_info(self.symbol)
        if symbol_info is None:
            raise ValueError(f"Failed to get symbol info for {self.symbol}")

        # Assuming a 2% stop loss
        stop_loss_pips = symbol_info.point * 200
        tick_value = symbol_info.trade_tick_value

        position_size = risk_amount / (stop_loss_pips * tick_value)
        return round(position_size, 2)

    def check_open_positions(self):
        positions = mt5.positions_get(symbol=self.symbol)
        return len(positions)

    def place_order(self, order_type):
        if self.check_open_positions() >= self.max_open_positions:
            print(f"Max open positions ({self.max_open_positions}) reached. Skipping order.")
            return

        lot_size = self.calculate_position_size()

        if order_type == 'BUY':
            price = mt5.symbol_info_tick(self.symbol).ask
            stop_loss = price - (200 * mt5.symbol_info(self.symbol).point)
            take_profit = price + (400 * mt5.symbol_info(self.symbol).point)
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": self.symbol,
                "volume": lot_size,
                "type": mt5.ORDER_TYPE_BUY,
                "price": price,
                "sl": stop_loss,
                "tp": take_profit,
                "deviation": 20,
                "magic": 234000,
                "comment": "python script open",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
        elif order_type == 'SELL':
            price = mt5.symbol_info_tick(self.symbol).bid
            stop_loss = price + (200 * mt5.symbol_info(self.symbol).point)
            take_profit = price - (400 * mt5.symbol_info(self.symbol).point)
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": self.symbol,
                "volume": lot_size,
                "type": mt5.ORDER_TYPE_SELL,
                "price": price,
                "sl": stop_loss,
                "tp": take_profit,
                "deviation": 20,
                "magic": 234000,
                "comment": "python script open",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
        else:
            return

        result = mt5.order_send(request)
        print(f"Order {order_type} sent: {result}")

    def run(self):
        while True:
            try:
                df = self.fetch_data(mt5.TIMEFRAME_M5, 100)
                df = self.analyze_data(df)
                signal = self.generate_signal(df)
                self.place_order(signal)
                time.sleep(300)  # Wait for 5 minutes before next iteration
            except Exception as e:
                print(f"An error occurred: {e}")
                time.sleep(60)  # Wait for 1 minute before retrying

    def __del__(self):
        mt5.shutdown()

# Usage
if __name__ == "__main__":
    algo = MT5TradingAlgorithm('EURUSD', 0.01, max_risk_percent=2, max_open_positions=3)
    algo.run()

