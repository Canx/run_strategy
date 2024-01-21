#!/usr/bin/env python
import sys
import argparse
import importlib
import inspect
from datetime import datetime, timedelta
from lumibot.traders import Trader
from lumibot.entities import TradingFee

def parse_arguments():
    """Parse command line arguments for running the strategy."""
    parser = argparse.ArgumentParser(description="Run a trading strategy.")
    parser.add_argument("strategy_file", help="The filename of the strategy to run")
    parser.add_argument("--live", action="store_true", help="Run the strategy in live mode")
    parser.add_argument("--broker", default='Kraken', choices=['IB', 'Kraken'], help="Broker to use for live trading (Interactive Brokers or Kraken)")
    parser.add_argument("--start", help="Backtesting start date in YYYY-MM-DD format")
    parser.add_argument("--end", help="Backtesting end date in YYYY-MM-DD format")
    return parser.parse_args()

def find_strategy_class(module):
    """Find and return the first strategy class in the given module."""
    for name, obj in inspect.getmembers(module, inspect.isclass):
        if obj.__module__ == module.__name__:
            return obj
    return None

def configure_broker(broker_choice):
    """Configure and return the broker for live trading based on user choice."""
    if broker_choice == 'IB':
        from credentials import INTERACTIVE_BROKERS_CONFIG
        from lumibot.brokers import InteractiveBrokers
        return InteractiveBrokers(INTERACTIVE_BROKERS_CONFIG)
    elif broker_choice == 'Kraken':
        from credentials import KRAKEN_CONFIG
        from lumibot.brokers import Ccxt
        return Ccxt(KRAKEN_CONFIG)
    else:
        raise ValueError("Invalid broker choice. Choose 'IB' for Interactive Brokers or 'Kraken'.")

def run_strategy(strategy_class, is_live, broker_choice, start_date, end_date):
    """Run the specified trading strategy in live or backtesting mode."""
    if is_live:
        # Confirm broker configuration
        print(f"Configured to run in live mode with broker: {broker_choice}")
        confirm = input("Do you want to proceed? (yes/no): ").lower()
        if confirm != 'yes':
            print("Operation cancelled.")
            return

        # Setting up for live trading
        trader = Trader()
        broker = configure_broker()
        strategy = strategy_class(broker=broker)
        trader.add_strategy(strategy)
        trader.run_all()
    else:
        # Setting up for backtesting
        from lumibot.backtesting import PolygonDataBacktesting
        from credentials import POLYGON_CONFIG

        # Getting yesterday's date
        yesterday = datetime.now() - timedelta(days=1)

        # Calculating one year from yesterday
        one_year_from_yesterday = yesterday - timedelta(days=365)

        # Setting the start and end dates for backtesting
        backtesting_start = start_date if start_date else one_year_from_yesterday
        backtesting_end = end_date if end_date else yesterday
        trading_fee = TradingFee(percent_fee=0.005)
        risk_free_rate = 5.233  # Fixed risk-free rate for backtesting

        print("Starting Backtest...")
        strategy_class.backtest(
            PolygonDataBacktesting,
            backtesting_start,
            backtesting_end,
            polygon_api_key=POLYGON_CONFIG["API_KEY"],
            polygon_has_paid_subscription=True,
            risk_free_rate=risk_free_rate,
            buy_trading_fees=[trading_fee],
            sell_trading_fees=[trading_fee],
            logfile=f'logs/{module_name}.log',
            parameters={}
        )

if __name__ == "__main__":
    # Main execution block
    args = parse_arguments()
    module_name = args.strategy_file.rsplit('.', 1)[0]

    try:
        # Dynamically import the strategy module and find the strategy class
        strategy_module = importlib.import_module(module_name)
        strategy_class = find_strategy_class(strategy_module)
        if not strategy_class:
            raise ImportError(f"No strategy class found in the module {module_name}.")
    except ImportError as e:
        print(f"Error importing strategy: {e}")
        exit(1)

    # Parse start and end dates for backtesting
    start_date = datetime.strptime(args.start, '%Y-%m-%d') if args.start else None
    end_date = datetime.strptime(args.end, '%Y-%m-%d') if args.end else None

    # Run the specified strategy
    run_strategy(strategy_class, args.live, args.broker, start_date, end_date)