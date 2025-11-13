## Deploy Actions
```
COMMON='--param endpoint http://192.168.49.1:9000 --param accessKey benji --param secretKey Benji2020! --param bucket imgreco'

wsk action create resize \
  --docker hibenji/openwhisk_resize resize/main.py \
  $COMMON \
  --annotation concurrency 5

wsk action create detect \
  --docker hibenji/openwhisk_detect detect/main.py \
  $COMMON \
  --annotation concurrency 5

wsk action create postprocess \
  --docker hibenji/openwhisk_postprocess postprocess/main.py \
  $COMMON \
  --annotation concurrency 5
```


## Sequence
```
wsk action create yolo-seq \
  --sequence resize,detect,postprocess \
  --annotation concurrency 5
```

```
wsk action invoke yolo-seq -r -p imageKey input/test.jpg -p size 640
```


## Update Actions
```
wsk action update resize \
  --docker hibenji/openwhisk_resize resize/main.py \
  $COMMON \
  --annotation concurrency 5

wsk action update detect \
  --docker hibenji/openwhisk_detect detect/main.py \
  $COMMON \
  --annotation concurrency 5

wsk action update postprocess \
  --docker hibenji/openwhisk_postprocess postprocess/main.py \
  $COMMON \
  --annotation concurrency 5

wsk action update yolo-seq \
  --sequence resize,detect,postprocess \
  --annotation concurrency 5
```

## Delete Actions
```
wsk action delete resize
wsk action delete detect
wsk action delete postprocess
wsk action delete yolo-seq
```