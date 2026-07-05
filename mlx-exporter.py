import time
import sys
import argparse
import smbus2
import logging
from prometheus_client import start_http_server, Gauge

# MLX90614 RAM registers for final temperatures
REG_TA    = 0x06
REG_TOBJ1 = 0x07
REG_TOBJ2 = 0x08

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger("mlx90614_exporter")

mlx_temp_gauge = Gauge(
    'mlx90614_temperature_celsius', 
    'MLX90614 sensor temperature readings in degrees Celsius.',
    ['sensor']
)

def auto_int(x):
    """Helper function to parse decimal/hex arguments."""
    return int(x, 0)

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Prometheus HTTP exporter for the MLX90614 IR temperature sensor."
    )
    
    parser.add_argument('-b', '--bus', type=int, default=1, 
                        help='I2C bus number (default: 1)')
    parser.add_argument('-d', '--address', type=auto_int, default=0x5A, 
                        help='I2C device address in decimal or hex like 0x5A (default: 0x5A)')
    parser.add_argument('-p', '--port', type=int, default=8000, 
                        help='Exporter HTTP port (default: 8000)')
    
    channel_group = parser.add_mutually_exclusive_group()
    channel_group.add_argument('-2', dest='channels', action='store_const', const=2,
                               help='2-channel operation: Ambient and Object 1')
    channel_group.add_argument('-3', dest='channels', action='store_const', const=3,
                               help='3-channel operation: Ambient, Object 1, and Object 2')
    
    parser.set_defaults(channels=2)
    
    return parser.parse_args()


def main():
    args = parse_arguments()
    
    try:
        start_http_server(args.port)
        logger.info("MLX90614 Prometheus Exporter started on port %d", args.port)
        logger.info("Configuration - Bus: %d, Address: %s, Channels: %d", 
                    args.bus, hex(args.address), args.channels)
    except Exception as e:
        logger.critical("Failed to start Prometheus HTTP server on port %d: %s", args.port, e)
        sys.exit(1)

    with smbus2.SMBus(args.bus) as bus:
        while True:
            try:
                raw_ta = bus.read_word_data(args.address, REG_TA)
                ta = round((raw_ta * 0.02) - 273.15, 2)
                mlx_temp_gauge.labels(sensor="ambient").set(ta)
                
                raw_tobj1 = bus.read_word_data(args.address, REG_TOBJ1)
                tobj1 = round((raw_tobj1 * 0.02) - 273.15, 2)
                mlx_temp_gauge.labels(sensor="object1").set(tobj1)
                
                if args.channels == 3:
                    raw_tobj2 = bus.read_word_data(args.address, REG_TOBJ2)
                    tobj2 = round((raw_tobj2 * 0.02) - 273.15, 2)
                    mlx_temp_gauge.labels(sensor="object2").set(tobj2)
                
            except OSError:
                # If an I2C glitch occurs, set active metrics to NaN
                mlx_temp_gauge.labels(sensor="ambient").set(float('nan'))
                mlx_temp_gauge.labels(sensor="object1").set(float('nan'))
                if args.channels == 3:
                    mlx_temp_gauge.labels(sensor="object2").set(float('nan'))

            time.sleep(10)

if __name__ == '__main__':
    main()
