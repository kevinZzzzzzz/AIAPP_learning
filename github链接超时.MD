1. 检查 Git 配置
首先，确保你的 Git 配置是正确的。你可以通过以下命令查看和设置代理配置：

git config --global --unset http.proxy
git config --global --unset https.proxy

2. 如果你使用代理服务器，请确保正确配置代理：
git config --global http.proxy http://127.0.0.1:7897
git config --global https.proxy https://127.0.0.1:7897

3. 测试网络连接
curl -v https://github.com

4. 刷新 DNS 缓存
Windowspn
  ipconfig /flushdns
macOS 和 Linux
  sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder
