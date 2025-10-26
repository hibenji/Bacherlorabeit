# Normal Action with failed Colorama

### make action:
`wsk action create test-colorama test_colorama.py --kind python:3`

### execute:
`wsk action invoke test-colorama --result`


# Building a new image with Colorama

### Build new image:
`./tutorials/local_build.sh -r python311Action -t action-python-colorama`


# Create new action with Colorama

### New action create:
`wsk action create test-colorama-new test_colorama.py --docker hibenji/action-python-colorama`

### Invoke:
`wsk action invoke test-colorama-new --result`

### Delete action:
`wsk action delete test-colorama-new`


# Create a new image with Opencv
### Build new image:
`./tutorials/local_build.sh -r python311Action -t action-python-opencv`
### New action create:
`wsk action create test-opencv test_opencv.py --docker hibenji/action-python-opencv`
### Invoke:
```
wsk action invoke test-opencv \
  --param-file <(echo '{"image_b64": "'$(cat test.txt)'"}') \
  --result
```

### Delete action:
`wsk action delete test-opencv`