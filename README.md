# read_video_generation

自动生成读单词的视频，效果如下：[样例视频](https://github.com/iioSnail/read_video_generation/raw/main/samples/samples.mp4)

> 由于生成单词需要访问Google Translation，因此需要科学上网

# 使用方式

使用colab生成：[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/iioSnail/read_video_generation/blob/master/colab.ipynb)

> Colab是Google的AI训练平台。我们免费可以使用该平台的计算资源，割资本主义韭菜。

# 详细参数

```
>> python gene_video.py -h
usage: gene_video.py [-h] [--filename FILENAME] [--repeat-times REPEAT_TIMES] [--interval INTERVAL] [--inner-interval INNER_INTERVAL] [--max-minutes MAX_MINUTES] [--video] [--no-video] [--background-color BACKGROUND_COLOR]
                     [--font-color FONT_COLOR] [--video-width VIDEO_WIDTH] [--video-height VIDEO_HEIGHT] [--max-font-size MAX_FONT_SIZE] [--cache-dir CACHE_DIR] [--output-dir OUTPUT_DIR]

optional arguments:
  -h, --help            show this help message and exit
  --filename FILENAME   单词文件的路径
  --repeat-times REPEAT_TIMES
                        重复次数
  --interval INTERVAL   两个单词的间隔时间(ms)
  --inner-interval INNER_INTERVAL
                        单词和释义的间隔时间(ms)
  --max-minutes MAX_MINUTES
                        单个音频最大时长(分钟)
  --video               生成视频
  --no-video            不生成视频
  --add-volume          加减音量（分贝）。例如：10是音量加10分贝，-10是减10分贝
  --low-pass-filter     过滤高音部分（护耳）。例如：8000表示过滤掉频率超过8k的频率
  --background-color BACKGROUND_COLOR
                        视频背景色
  --font-color FONT_COLOR
                        文字颜色
  --video-width VIDEO_WIDTH
                        视频宽
  --video-height VIDEO_HEIGHT
                        视频高
  --max-font-size MAX_FONT_SIZE
                        最大字体大小
  --cache-dir CACHE_DIR
                        生成的临时文件存放的目录
  --output-dir OUTPUT_DIR
                        输出文件的目录

```

# 代办事项

- [ ] 根据每行的情况自动调整字体大小 
- [ ] 支持增加背景图片，而非单调的颜色
- [ ] 增加英文文档
- [ ] 增加样例视频
- [ ] 视频生成加速，现在太慢了 