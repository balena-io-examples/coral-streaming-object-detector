import argparse, asyncio, json, os, cv2, platform, sys

from time import sleep
from aiohttp import web
from av import VideoFrame
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack, RTCIceServer, RTCConfiguration
from aiohttp_basicauth import BasicAuthMiddleware

from camera import CameraDevice
from peerconnection import PeerConnectionFactory
from rtcvideo import RTCVideoStream
import server

# from edgetpu.classification.engine import ClassificationEngine
from edgetpu.detection.engine import DetectionEngine
from edgetpu.utils import dataset_utils
from PIL import Image

async def offer(request):
    params = await request.json()
    offer = RTCSessionDescription(
        sdp=params['sdp'],
        type=params['type'])
    pc = pc_factory.create_peer_connection()
    pcs.add(pc)
    # Add local media
    local_video = RTCVideoStream(camera_device)
    pc.addTrack(local_video)
    @pc.on('iceconnectionstatechange')
    async def on_iceconnectionstatechange():
        if pc.iceConnectionState == 'failed':
            await pc.close()
            pcs.discard(pc)
    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    return web.Response(
        content_type='application/json',
        text=json.dumps({
            'sdp': pc.localDescription.sdp,
            'type': pc.localDescription.type
        }))

async def mjpeg_handler(request):
    boundary = "frame"
    response = web.StreamResponse(status=200, reason='OK', headers={
        'Content-Type': 'multipart/x-mixed-replace; '
                        'boundary=%s' % boundary,
    })
    await response.prepare(request)
    while True:
        data = await camera_device.get_jpeg_frame()
        await asyncio.sleep(0.2) # this means that the maximum FPS is 5
        await response.write(
            '--{}\r\n'.format(boundary).encode('utf-8'))
        await response.write(b'Content-Type: image/jpeg\r\n')
        await response.write('Content-Length: {}\r\n'.format(
                len(data)).encode('utf-8'))
        await response.write(b"\r\n")
        await response.write(data)
        await response.write(b"\r\n")
    return response

async def config(request):
    return web.Response(
        content_type='application/json',
        text=pc_factory.get_ice_config()
    )

async def on_shutdown(app):
    # close peer connections
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)

def checkDeviceReadiness():
    if not os.path.exists('/dev/video0') and platform.system() == 'Linux':
        print('Video device is not ready')
        sleep(1)
        sys.exit()
    else:
        print('Video device is ready')

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--model', help='File path of Tflite model.', required=True)
  parser.add_argument('--label', help='File path of label file.', required=True)
  parser.add_argument('--image', help='File path of the image to be recognized.', required=True)
  args = parser.parse_args()

  auth = []
  if 'username' in os.environ and 'password' in os.environ:
      print('\n#############################################################')
      print('Authorization is enabled.')
      print('Your balenaCam is password protected.')
      print('#############################################################\n')
      auth.append(BasicAuthMiddleware(username = os.environ['username'], password = os.environ['password']))
  else:
      print('\n#############################################################')
      print('Authorization is disabled.')
      print('Anyone can access your balenaCam, using the device\'s URL!')
      print('Set the username and password environment variables \nto enable authorization.')
      print('For more info visit: \nhttps://github.com/balena-io-playground/balena-cam')
      print('#############################################################\n')

  app = web.Application(middlewares=auth)
  app.on_shutdown.append(on_shutdown)
  app.router.add_get('/', server.index)
  app.router.add_get('/favicon.png', server.favicon)
  app.router.add_get('/balena-logo.svg', server.balena_logo)
  app.router.add_get('/balena-cam.svg', server.balena)
  app.router.add_get('/client.js', server.javascript)
  app.router.add_get('/style.css', server.stylesheet)
  app.router.add_post('/offer', offer)
  app.router.add_get('/mjpeg', mjpeg_handler)
  app.router.add_get('/ice-config', config)
  web.run_app(app, port=80)

checkDeviceReadiness()

pcs = set()
camera_device = CameraDevice()

# Factory to create peerConnections depending on the iceServers set by user
pc_factory = PeerConnectionFactory()

if __name__ == '__main__':
  main()