import time

print("Бот запущен и работает в фоне...")

while True:
    print("Still running...")
    time.sleep(10)

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
