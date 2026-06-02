import json
import re
from openai import OpenAI

# 1. 在这里填入你刚才申请的 API Key
client = OpenAI(
    api_key="sk-2cde96e1e2834076b144687dc1a46890",
    base_url="https://api.deepseek.com"
)


def extract_knowledge_from_text(cleaned_text: str) -> dict:
    """
    调用 DeepSeek 提取知识点并返回字典对象
    """
    system_prompt = """
    你是一个专业的计算机科学课程助教。你的任务是阅读用户提供的超长课件纯文本，尽可能全面、详尽地提取出核心章节信息和知识点，并严格以 JSON 格式输出。

    【输出格式要求】
    必须严格遵守以下 JSON 结构，不要输出任何 Markdown 标记（如 ```json），不要输出任何解释性文字或客套话，只能输出合法的 JSON 字符串：

    {
      "course_name": "提取或推断的课程名称",
      "chapter_id": "例如：ch04",
      "chapter_title": "提取的章节标题",
      "summary": "根据全文总结的章节详细摘要（约 150-300 字，请概括本章的所有核心逻辑）",
      "knowledge_points": [
        {
          "id": "kp001",
          "name": "知识点名称（尽量具体，例如不要只写‘排序’，要写‘归并排序的划分过程’）",
          "type": "必须从这四个词中选一个：concept / algorithm / difficulty / application",
          "importance": "必须从这三个词中选一个：core / important / extended",
          "description": "该知识点的深度解析。请包含其核心思想、关键步骤或应用场景，字数建议在 100-150 字之间，要有足够的干货,如果字数超过150也没关系，重要的是讲明白这个知识点。"
        }
      ]
    }

    【注意事项】
    1. type 字段只能是 concept、algorithm、difficulty、application 之一。
    2. importance 字段只能是 core、important、extended 之一。
    3. 【核心要求】请地毯式搜索全文，尽可能全面地覆盖文本中的所有重点内容，切勿遗漏，知识点数量建议在 15 到 35 个之间，如果超过也没关系，最重要的是覆盖全面，不要遗漏！
    """

    print("正在请求 DeepSeek 提取知识点，这可能需要十几秒到半分钟，请稍候...")
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"请提取以下课件文本的知识点：\n{cleaned_text}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )

        result_str = response.choices[0].message.content

        # 稳健性处理：去掉可能被大模型意外包裹的 markdown 标记
        result_str = re.sub(r'^```json\s*', '', result_str)
        result_str = re.sub(r'\s*```$', '', result_str)

        # 将字符串解析为 Python 字典
        knowledge_dict = json.loads(result_str)
        return knowledge_dict

    except json.JSONDecodeError:
        print("❌ JSON 解析失败，大模型返回的格式不正确。")
        print("原始返回内容如下：\n", result_str)
        return {}
    except Exception as e:
        print(f"❌ 调用 API 失败: {e}")
        return {}


def save_json(data: dict, filename: str):
    """将字典保存为 json 文件"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"✅ 成功保存至 {filename}")