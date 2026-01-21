# Web Interface Documentation

## Overview

The Cat Motion Detector now includes a web-based interface that allows you to monitor motion detection events in real-time from any device on your local network, including mobile phones and tablets.

## Features

- **Live Video Stream**: View an MJPEG stream of the most recent camera frames
- **Real-Time Alerts**: Get instant notifications when motion is detected via WebSocket
- **Detection History**: Scrollable list of recent motion events with timestamps and thumbnails
- **Responsive Design**: Mobile-friendly interface that works on phones, tablets, and desktops
- **Connection Status**: Visual indicator showing whether you're connected to the server

## Accessing the Web Interface

### From the Same Device (Laptop)

Once the application is running, open a web browser and navigate to:

```
http://localhost:5000
```

### From a Mobile Phone or Tablet (Same WiFi Network)

1. **Find your laptop's IP address**:

   On Linux:
   ```bash
   hostname -I | awk '{print $1}'
   ```
   
   Or check your network settings to find your local IP address (typically something like `192.168.1.100` or `10.0.0.50`)

2. **Open the web interface on your phone**:

   In your mobile browser, navigate to:
   ```
   http://YOUR_LAPTOP_IP:5000
   ```
   
   For example:
   ```
   http://192.168.1.100:5000
   ```

3. **Save as bookmark**: For quick access, save the page as a bookmark or add it to your home screen

## Configuration

The web interface can be configured via environment variables or by modifying the `config.py` file:

### Environment Variables

```bash
export WEB_HOST="0.0.0.0"      # Listen on all network interfaces (default)
export WEB_PORT="5000"          # Port number (default: 5000)
export DEBUG="false"            # Enable Flask debug mode (default: false)
```

### Change the Port

If port 5000 is already in use on your system, you can change it:

```bash
export WEB_PORT="8080"
python main.py
```

Then access the interface at `http://YOUR_IP:8080`

### Restrict Access to Localhost Only

For security, if you only want to access the web interface from the laptop itself:

```bash
export WEB_HOST="127.0.0.1"
python main.py
```

## How It Works

The web interface provides:

### Live Video Stream

- Displays real-time MJPEG video stream from your camera at ~10 FPS
- Automatically reconnects if the server restarts (no browser refresh needed)
- Shows a black screen when disconnected from the server

### Real-Time Event Notifications

- Instant notifications when motion is detected via WebSocket connection
- Events include timestamp and thumbnail image
- Maintains a scrollable history of up to 100 recent events
- Visual and animated alerts for new detections

## Troubleshooting

### Cannot Access from Mobile Phone

**Problem**: Web interface works on laptop but not on phone

**Solutions**:
1. Ensure both devices are on the same WiFi network
2. Check that `WEB_HOST` is set to `0.0.0.0` (not `127.0.0.1`)
3. Verify your laptop's firewall isn't blocking port 5000:
   ```bash
   sudo ufw allow 5000  # On Ubuntu/Debian
   ```
4. Double-check your laptop's IP address - it may change if using DHCP

### Video Feed Not Updating

**Problem**: Video stream shows black screen or doesn't update

**Solutions**:
1. Check that the camera is accessible and working
2. If the server was restarted, the video feed should automatically reconnect within a few seconds
3. Try refreshing the browser page if auto-reconnect doesn't work
4. Check browser console for JavaScript errors
5. Verify no other application is using the camera

### Connection Status Shows "Disconnected"

**Problem**: Red "Disconnected" status indicator

**Solutions**:
1. Ensure the Flask-SocketIO server is running (check terminal output)
2. Check browser console for WebSocket connection errors
3. Try using a different browser
4. Verify there are no proxy or VPN issues blocking WebSocket connections

### Port Already in Use

**Problem**: Error message "Address already in use"

**Solution**: Change the port number:
```bash
export WEB_PORT="8080"
python main.py
```

### Events Not Appearing

**Problem**: Motion is detected but events don't show in the web interface

**Solutions**:
1. Check terminal output - events should be printed when detected
2. Verify WebSocket connection is established (status should be "Connected")
2. Refresh the browser page
3. Check browser console for WebSocket errors
## Performance Considerations

- **Network Bandwidth**: MJPEG streaming consumes bandwidth. On cellular data, use WiFi when possible.
- **Multiple Clients**: Multiple devices can connect simultaneously and will all receive the same stream and events.
- **Event Storage**: Up to 100 recent events are stored in memory and cleared when the application restarts.

## Security Notes

**Important**: This web interface has NO authentication or encryption:

- Only use on trusted local networks
- Do NOT expose to the internet without adding authentication
- Do NOT use on public WiFi networks
- Consider the security implications before deployment

For production use, consider adding:
- HTTPS/TLS encryption
- Username/password authentication
- IP address whitelisting
- Rate limiting

## Future Enhancements

Potential improvements for the web interface:

- Authentication/login system
- Adjustable video quality and frame rate
- Event history persistence and search
- Configurable alert sounds
- Download event images or video clips
- Mobile app version
