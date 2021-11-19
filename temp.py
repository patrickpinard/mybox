from time import sleep
from ds18b20 import DS18B20

sensors = []

def main():
    sensor = DS18B20()
    n=9
    print(" --------- Mesure de température avec sonde DS18B20 ----------")
    while True:
        if n==0:
            n=5
            for sensor_id in DS18B20.get_available_sensors():
                sensors.append(DS18B20(sensor_id))

            for sensor in sensors:
                print("Sensor %s has temperature %.2f" % (sensor.get_id(), sensor.get_temperature()))
        else:
            n=n-1
        sleep(1)


if __name__ == "__main__":
    main()