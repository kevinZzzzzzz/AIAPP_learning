require('dotenv').config()

async function streamChat() {
  try {
    const response = await fetch(process.env.DEEPSEEK_BASE_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${process.env.DEEPSEEK_API_KEY}`
      },
      body: JSON.stringify({
        model: 'deepseek-v4-flash',
        messages: [
        //   { role: 'system', content: '你是一个前端开发助手' },
          { role: 'user', content: '解释一下Vue3的ref和reactive的区别，用生活类比' }
        ],
        stream: true  // 关键：开启流式
      })
    })

    // 处理流式响应
    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    
    let buffer = ''  // 用于处理可能的不完整数据块
    
    console.log('AI回复：\n')
    
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      // 解码收到的数据块
      const chunk = decoder.decode(value)
      buffer += chunk
      
      // SSE格式是以\n\n分隔的
      const lines = buffer.split('\n\n')
      buffer = lines.pop() || ''  // 最后一行可能不完整，留到下次处理
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)  // 去掉 'data: ' 前缀
          
          // 跳过 [DONE] 消息
          if (data === '[DONE]') continue
          
          try {
            const parsed = JSON.parse(data)
            const content = parsed.choices[0]?.delta?.content || ''
            if (content) {
              process.stdout.write(content)  // 逐字打印，不换行
            }
          } catch (e) {
            // 忽略解析错误（有时会有空行）
          }
        }
      }
    }
    
    console.log('\n\n 流式响应完成')
  } catch (error) {
    console.error('请求失败：', error)
  }
}

streamChat()
