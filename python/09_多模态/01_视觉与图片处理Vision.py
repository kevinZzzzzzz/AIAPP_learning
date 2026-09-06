# 概念代码：演示多模态（视觉理解与生成）在 AI 应用中的形态
def main():
    print("--- 视觉大模型 (Vision Model) 概念演示 ---")
    
    print("\n[场景 1：图片理解 (Image to Text)]")
    print("前端传入：用户上传了一张网页设计稿截图 (base64 或 图片 URL)")
    print("后端调用：请求 GPT-4o-vision 或 Claude-3.5-sonnet")
    print("Prompt: '请帮我把这张设计稿转换成基于 TailwindCSS 的 React 代码。'")
    print("AI 返回：<生成的前端代码>")
    
    print("\n[场景 2：图片生成 (Text to Image)]")
    print("前端传入：用户输入 '一只穿着宇航服的猫在月球弹吉他'")
    print("后端调用：请求 DALL-E 3 或 Midjourney API")
    print("AI 返回：https://image.url/cat.png")
    
    print("\n[前端开发者的优势]:")
    print("多模态应用非常依赖前端交互！比如拖拽上传图片、图片裁剪、在图片上框选特定区域作为焦点传给 AI，这些都是前端的强项。")

if __name__ == "__main__":
    main()
