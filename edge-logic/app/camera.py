import asyncio, json, os, cv2, platform, sys
from time import sleep
from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack, RTCIceServer, RTCConfiguration
from aiohttp_basicauth import BasicAuthMiddleware

import detect

class CameraDevice():
    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        ret, frame = self.cap.read()
        if not ret:
            print('Failed to open default camera. Exiting...')
            sys.exit()
        self.cap.set(3, 640)
        self.cap.set(4, 480)

    def rotate(self, frame):
        # TODO: allow to configure camera orientation
        (h, w) = frame.shape[:2]
        center = (w/2, h/2)
        M = cv2.getRotationMatrix2D(center, 180, 1.0)
        frame = cv2.warpAffine(frame, M, (w, h))
        return frame

    async def get_latest_frame(self):
        ret, frame = self.cap.read()

        img = detect.objects(frame)
        await asyncio.sleep(0)
        # return self.rotate(img)
        return img