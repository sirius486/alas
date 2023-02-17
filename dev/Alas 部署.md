# 在 Linux 上部署 AzurLaneAutoScript

需要基本的 bash、Linux、git 知识


## 拉取仓库

在欲安装 alas 的目录下执行

```bash
git clone git@github.com:sirius486/alas.git
# 或 git clone https://github.com/sirius486/alas.git
```
克隆整个 git 仓库


## 安装依赖

### 1. python 环境
建议使用 virtualenv 或 conda 等 python 环境管理工具，以 conda 为例

```bash
conda create -n alas python=3.7.6
conda activate alas
cd AzurLaneAutoScript
pip install -r requirements-in.txt -i https://pypi.douban.com/simple/ # 或使用其它稳定源
```
> 由于某些 python 库在不同 os 下的依赖不同，直接从 requirements-in.txt 安装即可，pip会自动处理依赖。当然也可以从 requirements.txt 安装，但是需注释掉 pywin32

### 2. adb

下载 [SDK Platform Tools](https://developer.android.com/studio/releases/platform-tools) for Linux 并解压，将adb放在 `/usr/bin/` 目录下，因为 alas 只能读取此处的 adb 可执行文件

### 3. uiautomator2

若运行 alas 后无法正常初始化 uiautomator2，可按此方法手动安装，安装过程参考 [uiautomator2](https://github.com/openatx/uiautomator2)

运行 `adb connect <address>` 连接你的云手机，确保运行 `adb device` 后可以看到设备

在 alas python 环境下运行 `python` 打开 python 命令行窗口，输入以下命令

```python
import uiautomator2 as u2

d = u2.connect() # connect to device
print(d.info)
```

等待一段时间，输出类似如下内容，说明安装成功

```python
{'currentPackageName': 'net.oneplus.launcher', 'displayHeight': 1920, 'displayRotation': 0, 'displaySizeDpX': 411, 'displaySizeDpY': 731, 'displayWidth': 1080, 'productName': 'OnePlus5', '
screenOn': True, 'sdkInt': 27, 'naturalOrientation': True}
```


## 自动更新设置（可选）

若需在本地修改代码等，可设置 `AzurLaneAutoScript/config/deploy.yaml` 中的 `Deploy.Update` 部分，关闭自动更新，采用 git 等方式手动进行版本控制。

## Web UI 密码

由于云服务器暴露在公网中，出于安全起见请设置 `AzurLaneAutoScript/config/deploy.yaml` 中 `Deploy.Webui.Password` 项，作为访问密码

## 使用 shell 脚本启动停止 alas

根据实际安装位置编辑以下脚本内容

```bash
#!/bin/bash

start(){
    source <conda_path>/bin/activate alas # <miniconda_path> 替换为实际 conda 安装路径
    cd <AzurLaneAutoScript_path> # <AzurLaneAutoScript_path> 替换为 alas 路径
    nohup python gui.py >/dev/nul 2>&1 &
    echo "start gui.py"
}

stop(){
    pkill -9 -f "python gui.py"
    echo "kill gui.py"
}

case $1 in
    "start" ) start;;
    "stop" ) stop;;
    * ) stop;start;;
esac
```

将文件保存为 alas，然后执行

```bash
chmod 755 alas
```
更改权限。

可将脚本文件所在目录放入 PATH 中，则可用以下命令控制 alas

```bash
alas start # 启动
alas stop # 停止
alas # 重启
```


## 注意事项

* minitouch 的可用性疑似不稳定
* 我出现了点击网页 `停止` 按钮后 alas 所有进程崩溃的情况，但未能在其他服务器复现
* 如果服务器配置了防火墙，请放行TCP 5037 和 22267 端口，这分别是 adb 和 alas Web UI 的监听端口