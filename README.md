# Read Video Generation

本项目可以帮助用户快速生成自定义的“阅读视频”，即视频中仅包含简单的文字和语音。

结果视频样例：

TODO

# 使用样例

```shell
python gene_video.py --file ./samples/read_sentence.json  --output output.mp4
```

# 使用说明

## 参数说明

生成视频需要传如下参数：


```
(base) D:\PythonProjects\read_video_generation>python gene_video.py -h
usage: gene_video.py [-h] --file FILE [--output OUTPUT] [--interval INTERVAL] [--background BACKGROUND] [--width WIDTH] [--height HEIGHT] [--framerate FRAMERATE] [--cache-dir CACHE_DIR] [--proxy PROXY]

optional arguments:
  --file FILE           JSON文件的路径，该文件描述了具体的视频内容
  --output OUTPUT       输出文件的路径。例如：output.mp4
  --interval INTERVAL   两段视频之间间隔多少秒。默认为500ms
  --background BACKGROUND
                        视频的背景图片（尽量和视频宽高保持一致，否则会被拉伸）. 默认值: ./assert/background.png
  --width WIDTH         视频的宽度。 默认值: 1920
  --height HEIGHT       视频的高度. 默认值: 1080
  --framerate FRAMERATE
                        视频的帧率. 默认值: 24
  --cache-dir CACHE_DIR 缓存目录. 视频生成过程中会产生一些中间文件，会被存在该目录下。若生成中断或报错，则部分内容不用重复生成。
  --proxy PROXY         edge-tts的代理。文本转语音需要调用微软的API，中国网络你懂得，可能需要上代理。样例: http://127.0.0.1:1080
```

## 构造JSON

用户在使用前需要构造一个json文件来描述视频的具体内容，样例如下：

```json5
[  // json为一个list，每一项包含一张图片和一段音频。
  {
    "frame": {  // frame描述了当前图片展示的内容
      "elements": [  // elements为list，里面描述了不同位置展示的不同文字。
        {
          "x_coord": 0.05,  // 当前文本在哪个位置展示。该坐标为相对坐标，即左上角是(0,0)，右下角是(1,1)
          "y_coord": 0.05,
          "coord_type": "top-left",  // 坐标类型。top-left: (x,y)对应当前元素的左上角。center: (x,y)对应元素的中心
          "font_size": 80,  // 字体大小
          "font_color": "white",  // 字体颜色
          "content": "1"  // 文本内容
        },
        {
          "x_coord": 0.5,
          "y_coord": 0.3,
          "coord_type": "center",
          "font_size": 90,
          "font_color": "white",
          "content": "I've heard about that one"
        }
      ]
    },
    "audio": {  // audio描述了当前项的音频如何展示
      "elements": [  // 通常一张图片可能会对应多段音频。因此这里是list
        {
          "text": "I've heard about that one",  // 朗读的文本
          "tts_name": "en-US-AriaNeural",  // 使用谁的声音
          "before_silence": 200,  // 在读这段文字前，插入200ms的无声音频
          "after_silence": 500  // 在读完这段文字后，插入500ms的无声音频
        },
        {
          "text": "我听说过那个",
          "tts_name": "zh-CN-YunyangNeural",
          "after_silence": 200
        }
      ],
      "interval": 1000  // elements中的每段音频间隔多久。若指定该值，通常就不用再指定“before_silence”和“after_silence”。
    }
  }
  // ...
]
```


# 代办事项

- [ ] 增加英文文档
- [ ] 增加样例视频