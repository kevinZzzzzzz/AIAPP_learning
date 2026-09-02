require('dotenv').config()

async function callDeepSeek() {
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
          { role: 'user', content: 'hello' }
        ],
        stream: false  // 非流式
      })
    })

    if (!response.ok) {
      const text = await response.text()
      throw new Error(`HTTP ${response.status} ${response.statusText}\n${text}`)
    }

    const data = await response.json()
    console.log('AI回复：')
    console.log(data.choices[0].message.content)
  } catch (error) {
    console.error('请求失败：', error)
  }
}

callDeepSeek()
