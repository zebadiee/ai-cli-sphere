import time

def simulate_token_processing(token_data):
    """Simulates processing a token."""
    time.sleep(0.001)  # Simulate some work
    return f"Processed: {token_data}"

def run_performance_test(num_tokens=1000):
    start_time = time.time()
    for i in range(num_tokens):
        simulate_token_processing(f"token_{i}")
    end_time = time.time()
    print(f"Processed {num_tokens} tokens in {end_time - start_time:.4f} seconds.")
    print(f"Average time per token: {(end_time - start_time) / num_tokens * 1000:.4f} ms")

if __name__ == "__main__":
    print("Running performance test...")
    run_performance_test()
