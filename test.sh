echo "Starting receiver"
python src/receiver/main.py &

echo "Starting sender"
python src/sender/main.py
