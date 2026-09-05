"""
LiteRT-LM Inference Server (subprocess)
Runs as a separate process under Python 3.11+ to handle LiteRT-LM inference.
Communicates with the main backend via stdin/stdout JSON messages.

Protocol:
  -> {"type": "generate", "prompt": "...", "system": "...", "max_tokens": 512}
  <- {"type": "token", "text": "..."}
  <- {"type": "done"}

  -> {"type": "ping"}
  <- {"type": "pong"}

  -> {"type": "shutdown"}
"""
import sys
import json
import traceback

def main():
    model_path = sys.argv[1] if len(sys.argv) > 1 else None
    if not model_path:
        _send({"type": "error", "message": "No model path provided"})
        sys.exit(1)

    _send({"type": "status", "message": f"Loading LiteRT-LM model: {model_path}"})

    try:
        import litert_lm
        engine = litert_lm.Engine(model_path)
        engine.__enter__()
        _send({"type": "ready", "message": "LiteRT-LM engine loaded"})
    except Exception as e:
        _send({"type": "error", "message": f"Failed to load engine: {e}"})
        sys.exit(1)

    conversation = None

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            _send({"type": "error", "message": f"Invalid JSON: {line}"})
            continue

        msg_type = msg.get("type")

        if msg_type == "ping":
            _send({"type": "pong"})

        elif msg_type == "generate":
            prompt = msg.get("prompt", "")
            system_prompt = msg.get("system", "")
            max_tokens = msg.get("max_tokens", 512)

            try:
                # Create a fresh conversation for each request
                messages = []
                if system_prompt:
                    messages.append(litert_lm.Message.system(system_prompt))

                conv = engine.create_conversation(messages=messages)
                conv.__enter__()

                # Stream response
                for chunk in conv.send_message_async(prompt):
                    # Extract text from chunk — structure varies by version
                    text = ""
                    if isinstance(chunk, dict):
                        content = chunk.get("content", [])
                        if isinstance(content, list) and content:
                            text = content[0].get("text", "")
                        elif isinstance(content, str):
                            text = content
                    elif isinstance(chunk, str):
                        text = chunk

                    if text:
                        _send({"type": "token", "text": text})

                conv.__exit__(None, None, None)
                _send({"type": "done"})

            except Exception as e:
                _send({"type": "error", "message": f"Generation error: {traceback.format_exc()}"})
                _send({"type": "done"})

        elif msg_type == "shutdown":
            _send({"type": "status", "message": "Shutting down"})
            break

    # Cleanup
    try:
        engine.__exit__(None, None, None)
    except:
        pass


def _send(obj):
    """Send a JSON message to stdout."""
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
