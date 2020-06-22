import argparse, asyncio, json, os, cv2, platform, sys

from time import sleep
from aiohttp import web
from av import VideoFrame
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack, RTCIceServer, RTCConfiguration
from aiortc.contrib.media import MediaPlayer
from aiohttp_basicauth import BasicAuthMiddleware

from camera import CameraDevice
from peerconnection import PeerConnectionFactory
from rtcvideo import RTCVideoStream
import server

from edgetpu.detection.engine import DetectionEngine
from edgetpu.utils import dataset_utils
from PIL import Image

import logging

LOGLEVEL = os.environ.get('LOGLEVEL', 'INFO').upper()
logging.basicConfig(level=LOGLEVEL)

async def offer(request):
    params = await request.json()
    offer = RTCSessionDescription(
        sdp=params['sdp'],
        type=params['type'])
    pc = pc_factory.create_peer_connection()
    pcs.add(pc)
    # Add local media
    local_video = RTCVideoStream(player)
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
        data = await player.get_jpeg_frame()
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
        logging.error('Video device is not ready\n')
        sleep(1)
        sys.exit()
    else:
        logging.info('Video device is ready\n')

def main():

  auth = []
  if 'username' in os.environ and 'password' in os.environ:
      logging.info('#############################################################')
      logging.info('Authorization is enabled.')
      logging.info('Your balenaCam is password protected.')
      logging.info('#############################################################\n')
      auth.append(BasicAuthMiddleware(username = os.environ['username'], password = os.environ['password']))
  else:
      logging.info('#############################################################')
      logging.info('Authorization is disabled.')
      logging.info('Anyone can access your balenaCam, using the device\'s URL!')
      logging.info('Set the username and password environment variables to enable authorization.')
      logging.info('For more info visit: https://github.com/balena-io-playground/balena-cam')
      logging.info('#############################################################\n')

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

  web.run_app(app, access_log=None, port=80)

pcs = set()

# open media source
if "CAMERA" in os.environ:
    checkDeviceReadiness()
    #Load Camera based on environment variable, default to /dev/video0
    player = CameraDevice(int(os.getenv('CAMERA', 0)))
else:
    player = CameraDevice("/usr/src/video/construction.mp4")

# Factory to create peerConnections depending on the iceServers set by user
pc_factory = PeerConnectionFactory()

if __name__ == '__main__':
  main()