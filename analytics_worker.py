import asyncio
import json
import redis.asyncio as redis

# Connect to Redis
redis_client = redis.Redis.from_url("redis://localhost:6379/0", decode_responses=True)
STREAM_KEY = "clicks:stream"
GROUP_NAME = "analytics_group"

async def main():
    # 1. Create a Consumer Group (so Redis knows who is reading the stream)
    try:
        await redis_client.xgroup_create(STREAM_KEY, GROUP_NAME, id="0", mkstream=True)
        print("Created consumer group.")
    except redis.exceptions.ResponseError:
        print("Consumer group already exists.")

    print("Listening for clicks...")
    
    # 2. Endlessly loop and read new messages
    while True:
        try:
            # Block for up to 5 seconds waiting for new data (">" means unread messages)
            messages = await redis_client.xreadgroup(GROUP_NAME, "worker-1", {STREAM_KEY: ">"}, count=10, block=5000)
            
            if not messages:
                continue

            for stream, msg_list in messages:
                for message_id, data in msg_list:
                    
                    print(f"🔥 CLICK DETECTED! URL: {data['short_code']} | IP: {data['ip_address']} | Time: {data['timestamp']}")
                    
                    # ----------------------------------------------------
                    # IN A REAL APP, YOU WOULD SAVE TO A DATABASE HERE!
                    # e.g., INSERT INTO analytics_table (ip, user_agent...)
                    # ----------------------------------------------------

                    # 3. Acknowledge (XACK) the message so Redis deletes it from the pending list
                    await redis_client.xack(STREAM_KEY, GROUP_NAME, message_id)

        except Exception as e:
            print(f"Error: {e}")
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())