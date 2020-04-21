#!/bin/bash

#Copy model and labels to shared volume
echo "Copying Model to shared volume..."
cp -v *{tflite,txt} shared-model/