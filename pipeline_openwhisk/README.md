## Deploy Actions
```
COMMON='--param endpoint http://192.168.49.1:9000 --param accessKey benji --param secretKey Benji2020! --param bucket imgreco'

wsk action create resize --docker hibenji/action-python-opencv resize/main.py $COMMON
wsk action create detect --docker hibenji/action-python-opencv detect/main.py $COMMON
wsk action create postprocess --docker hibenji/action-python-opencv postprocess/main.py $COMMON
```


## Sequence
```
wsk action create yolo-seq --sequence resize,detect,postprocess
```

```
wsk action invoke yolo-seq -r -p imageKey input/test.jpg -p size 640
```


## Update Actions
```
wsk action update resize --docker hibenji/action-python-opencv resize/main.py $COMMON
wsk action update detect --docker hibenji/action-python-opencv detect/main.py $COMMON
wsk action update postprocess --docker hibenji/action-python-opencv postprocess/main.py
wsk action update yolo-seq --sequence resize,detect,postprocess
```

## Delete Actions
```
wsk action delete resize
wsk action delete detect
wsk action delete postprocess
wsk action delete yolo-seq
```