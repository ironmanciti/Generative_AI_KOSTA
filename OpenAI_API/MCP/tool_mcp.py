# tool_mcp.py
import asyncio
import requests
from dotenv import load_dotenv

from agents import Agent, Runner, function_tool
from agents.mcp import MCPServerStdio

load_dotenv()

@function_tool
def get_weather(위도: float, 경도: float) -> str:
    """주어진 위도/경도 좌표의 현재 기온(°C)을 문자열로 반환"""
    latitude = 위도
    longitude = 경도
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={latitude}&longitude={longitude}&current=temperature_2m"
    )
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    temp = data.get("current", {}).get("temperature_2m")
    return f"{temp}°C" if temp is not None else "알 수 없음"

async def main():
    
    # 두 MCP 서버를 모두 컨텍스트 매니저로 사용
    async with MCPServerStdio(
        name="Playwright MCP",
        params={
            "command": "npx",
            "args": ["-y", "@playwright/mcp@latest"],
        },
    ) as playwright_mcp_server:

        agent = Agent(
            name="여행 에이전트",
            model="gpt-5-mini",  
            instructions=(
                "당신은 훌륭한 여행 에이전트입니다. "
                "여행 일정을 짤 때 웹검색(Playwright MCP)도 활용하고, "
                "가능하면 출처(URL)도 같이 표시해 주세요. "
                "날씨가 필요하면 get_weather(위도,경도) 도구를 사용하세요. "
            ),
            tools=[get_weather],
            mcp_servers=[playwright_mcp_server],
        )

        messages = []
        print("\n 여행 에이전트와 대화를 시작합니다. 종료하려면 'exit' 입력.\n")

        while True:
            try:
                user_input = input("\n사용자: ").strip()
                if user_input.lower() == "exit":
                    print("안녕히 가세요!")
                    break

                messages.append({"role": "user", "content": user_input})
                print("\n여행 에이전트: ", end="", flush=True)

                response = await Runner.run(agent, input=messages)
                # RunResult 객체에서 텍스트 추출
                if hasattr(response, 'text') and response.text:
                    full = response.text
                elif hasattr(response, 'content') and response.content:
                    full = response.content
                elif hasattr(response, 'output'):
                    # output 리스트에서 텍스트 타입 항목 찾기
                    text_items = []
                    for item in response.output:
                        if hasattr(item, 'content') and item.content:
                            text_items.append(str(item.content))
                        elif isinstance(item, str):
                            text_items.append(item)
                        elif hasattr(item, 'text') and item.text:
                            text_items.append(str(item.text))
                    full = ' '.join(text_items) if text_items else str(response)
                elif hasattr(response, 'message') and hasattr(response.message, 'content'):
                    full = response.message.content
                else:
                    full = str(response)
                print(full)

                messages.append({"role": "assistant", "content": full})
                
            except KeyboardInterrupt:
                print("\n\n 종료합니다.")
                break
            except Exception as e:
                print(f"\n 오류 발생: {e}")
                continue

if __name__ == "__main__":
    asyncio.run(main())