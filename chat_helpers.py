from claude_client import client, MODEL

# O(L) where L = response length, bounded by max_tokens
def strip_fences(json_text):
    look_start = json_text.find('[')
    look_end = json_text.rfind(']')
    start = json_text.find('{')
    end = json_text.rfind('}')


    if (look_start != -1) and (look_start < start):

        if (look_start == -1) or (look_end == -1):
            return json_text
        else:
            parsable_json = json_text[look_start:look_end + 1]
            return parsable_json
    else:
        if (start == -1) or (end == -1):
            return json_text
        else:
            parsable_json = json_text[start:end + 1]
            return parsable_json


def add_user_message(messages, text):
    messages.append({"role": "user", "content": text})


def add_assistant_message(messages, text):
    messages.append({"role": "assistant", "content": text})


def chat(messages, system=None, stop_sequences=[]):
    response3 = []
    params = {
        "model": MODEL,
        "max_tokens": 1500,
        "messages": messages,
        "stop_sequences": stop_sequences,
    }

    if system:
        params["system"] = system

    response = client.messages.create(**params)
    #The 3 lines below were for debugging faulty json output by Claude

    #print(len(response.content),  response.stop_reason)
    #for responses in response.content:
        #print(responses.type)

    text_response = response.content

    for x in text_response:
        if x.type == "text":
            response3.append(x.text)
    joined_response = ''.join(response3)
    return joined_response


