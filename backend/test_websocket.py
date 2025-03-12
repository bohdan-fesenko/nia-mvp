#!/usr/bin/env python3
"""
WebSocket Test Script

This script tests the WebSocket connection to the backend server.
It can be used to verify that the WebSocket server is running and
that authentication is working correctly.
"""

import asyncio
import json
import sys
import websockets
import argparse
from datetime import datetime

# Default WebSocket URL
DEFAULT_WS_URL = "ws://localhost:8000/api/v1/ws"

async def test_websocket(url, token=None, dev_mode=False):
    """
    Test the WebSocket connection to the backend server.
    
    Args:
        url (str): The WebSocket URL to connect to
        token (str, optional): Authentication token
        dev_mode (bool, optional): Whether to use dev mode
    """
    # Add authentication parameters if provided
    if token:
        url = f"{url}?token={token}"
    elif dev_mode:
        url = f"{url}?dev_mode=true"
        
    print(f"Connecting to {url}...")
    
    try:
        async with websockets.connect(url) as websocket:
            print("Connected to WebSocket server!")
            
            # Send a ping message
            ping_message = {
                "type": "ping",
                "data": {
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            print(f"Sending ping: {json.dumps(ping_message)}")
            await websocket.send(json.dumps(ping_message))
            
            # Wait for a response
            print("Waiting for response...")
            response = await websocket.recv()
            
            # Parse and display the response
            try:
                parsed_response = json.loads(response)
                print(f"Received response: {json.dumps(parsed_response, indent=2)}")
                
                # Check if it's a pong message
                if parsed_response.get("type") == "pong":
                    print("✅ Successfully received pong response!")
                else:
                    print(f"⚠️ Received message of type: {parsed_response.get('type', 'unknown')}")
            except json.JSONDecodeError:
                print(f"❌ Received non-JSON response: {response}")
            
            # Keep the connection open for a moment to receive any additional messages
            print("Waiting for additional messages (5 seconds)...")
            for _ in range(5):
                try:
                    # Set a timeout for receiving messages
                    response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    try:
                        parsed_response = json.loads(response)
                        print(f"Received message: {json.dumps(parsed_response, indent=2)}")
                    except json.JSONDecodeError:
                        print(f"Received non-JSON message: {response}")
                except asyncio.TimeoutError:
                    # No message received within the timeout
                    await asyncio.sleep(1)
                    continue
            
            print("Test completed successfully!")
            
    except websockets.exceptions.ConnectionClosed as e:
        print(f"❌ Connection closed: {e}")
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ Invalid status code: {e}")
        if e.status_code == 401:
            print("Authentication failed. Check your token or try using dev mode.")
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    """Parse command line arguments and run the test."""
    parser = argparse.ArgumentParser(description="Test WebSocket connection to the backend server")
    parser.add_argument("--url", default=DEFAULT_WS_URL, help=f"WebSocket URL (default: {DEFAULT_WS_URL})")
    parser.add_argument("--token", help="Authentication token")
    parser.add_argument("--dev-mode", action="store_true", help="Use development mode")
    
    args = parser.parse_args()
    
    if args.token and args.dev_mode:
        print("Warning: Both token and dev-mode are specified. Token will be used.")
    
    asyncio.run(test_websocket(args.url, args.token, args.dev_mode))

if __name__ == "__main__":
    main()