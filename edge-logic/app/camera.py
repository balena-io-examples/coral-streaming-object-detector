import asyncio, cv2, sys
from time import sleep
from PIL import Image
import detect

class CameraDevice():
    def __init__(self, input):
        self.cap = cv2.VideoCapture(input)
        ret, frame = self.cap.read()
        if not ret:
            print('Failed to open default camera. Exiting...')
            sys.exit()
        self.cap.set(3, 640)
        self.cap.set(4, 480)

    async def get_latest_frame(self):
        try:
            ret, frame = self.cap.read()

            img = detect.objects(frame)
            await asyncio.sleep(0)
            return img
        except:
            print('Video stream ended. Exiting...')
            sys.exit()
    
    async def get_jpeg_frame(self):
        encode_param = (int(cv2.IMWRITE_JPEG_QUALITY), 90)
        frame = await self.get_latest_frame()
        frame, encimg = cv2.imencode('.jpg', frame, encode_param)
        return encimg.tostring()