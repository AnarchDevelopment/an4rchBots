# an4rchBots

A Python-based bot framework for connecting multiple clients to a Minecraft Pocket Edition (MCPE) server. The project creates bots that connect, authenticate, send chat messages, move, and maintain an active session.

## Project Structure

- `main.py`: Main entry point. Initializes bots, resolves the server host, checks server status, launches connections, and runs the interactive console.
- `state.py`: Shared global state and synchronization primitives for bots.
- `Connection/SpawnBot.py`: Bot lifecycle and interaction logic, including packet handling, movement, chat, and spam.
- `Host/ResolveHost.py`: DNS resolution and IP validation for server hosts.
- `Player/BotName.py`: Random bot name generator.
- `Player/Skin.py`: Random skin data generator for bots.
- `Crypto/EC.py`: ECDSA key generation for JWT creation.
- `Crypto/JWT.py`: JWT construction for MCPE login.
- `RakNet/Packet.py`: RakNet packet utilities for reading and writing binary data.
- `RakNet/Protocol.py`: Protocol constants and packet builders for MCPE.
- `RakNet/RakNet.py`: RakNet transport implementation, reliable packet sending, and connection management.

## Requirements

- Python 3.8 or higher
- `cryptography`

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

## Usage

Run the project from the repository root:

```powershell
python main.py <host> <port> <name> <bots> <time> [protocol] [register] [messages] [interval]
```

### Arguments

- `<host>`: Server IP or domain name.
- `<port>`: Server UDP port.
- `<name>`: Base name used for bot accounts.
- `<bots>`: Number of bots to create.
- `<time>`: Duration in seconds to run. Use `0` for unlimited runtime.
- `[protocol]`: Optional. `70` or `84`. Defaults to `84`.
- `[register]`: Optional register command or static password. If it starts with `/`, it sends the command with a random password.
- `[messages]`: Optional messages separated by `|` to send via bot chat.
- `[interval]`: Optional interval in seconds between spam messages.

### Example

```powershell
python main.py play.example.com 19132 bot 20 120 84 /register Hello!-How-are-you? 5
```

## Console Commands

After startup, the following commands are available:

- `help` - Show available commands.
- `status` - Display bot status table.
- `say <message>` - Send a message or command from all bots.
- `move` - Toggle automatic movement for bots.
- `jump` - Make all moving bots jump.
- `autojump` - Toggle random auto-jumps.
- `spam` - Toggle chat spam.
- `tp <x> <y> <z>` - Teleport all bots to the specified coordinates.
- `distribute` - Spread bots randomly around their current positions.
- `reconnect` - Force reconnection for all bots.
- `info` - Show current session information.
- `exit` - Stop the program and disconnect all bots.

## Notes

- This project uses RakNet and MCPE protocol packets to emulate client behavior.
- It is designed for MCPE servers compatible with protocol 0.15.x when using protocol `84`.
- If host resolution fails or the server is offline, the program exits.

# Warning
Bots may experience partial or complete failure in the movement and messaging system due to the somewhat unusual or limited PocketMine packages. This tool was created for legitimate educational purposes; do not test it on servers to take them down or disable them.

This script may violate the [Minecraft EULA](https://www.minecraft.net/en-us/eula) if not used correctly.

## License

This project is under of the licence [MIT Licence](LICENSE)
