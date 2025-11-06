import socket
import re
from typing import List
import os

def clean_code_string(code_string):
    # Remove ```python or other language specifier and the closing ```
    return re.sub(r"```[a-zA-Z]*\n|```", "", code_string).strip()

def concat_calls_code(example_calls: List[str]):
    # Loop through the code_calls and dynamically add code for each call and path assignment
    content = ""
    content += "import ghpythonlib.treehelpers as th\n"
    content += "    from Grasshopper.Kernel.Data import GH_Path\n"
    content += "    geometry_states = []\n"
    for i, call in enumerate(example_calls):
        content += f"    # Generate sample geometry {i+1}/{len(example_calls)}\n"
        content += f"    {call}\n"
        content += f"    geometry = list(geometry) if not isinstance(geometry, list) else geometry\n"
        content += "    geometry_states.append(geometry)\n\n"
    content += "    # Convert the list of geometries to a Grasshopper DataTree\n"
    content += "    geometry_states = th.list_to_tree(geometry_states)\n"
    return content

def _prepare_code_for_gh(function_code: str, example_calls: List[str]):
    # Dynamically generate the code that defines 'function_calls' as a list
    # function_calls_list = ",\n".join(f'"{call}"' for call in code.code_calls)
    # code_function = code.code_function.replace('"""', '\\"""')
    calls_code = concat_calls_code(example_calls)
    function_code = function_code.replace('"""', '\\"""')
    code_to_send = "#! python 3\n"
    code_to_send += f'function_code = """{function_code}"""\n'
    code_to_send += f"""
try:
    exec(function_code)
    {calls_code}
    print("success")
except Exception as e:
    print("Error: ", e)
"""
    return code_to_send

def _send_code_to_grasshopper(message):
    # Define the server address and port
    server_address = ("localhost", 12346)
    # Define the server address and port
    receive_server_address = ("localhost", 12347)

    # Create a UDP socket
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        # Send the message
        udp_socket.sendto(message.encode(), server_address)
        print(f"Sent: {message}")
        udp_socket.close()
        print("Message sent. Waiting for response...")
        # Enter a loop to listen for the response
        # Create a UDP socket
        new_udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Set the socket option to reuse the address
        new_udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Bind the socket to the server address
        new_udp_socket.bind(receive_server_address)
        while True:

            # Receive the response from the receiver
            data, addr = new_udp_socket.recvfrom(4096)

            # Print the received response
            print(f"Received response from {addr}.")
            return data.decode()

            # Break the loop after receiving the first response
            # break
    finally:
        udp_socket.close()
        new_udp_socket.close()
        print("Closed socket")

def save_script_to_file(path, gh_code, summary):
    # Extract the function name from the 'code_func' by splitting at 'def' and '('
    # func_name = gh_code.split("def ")[1].split("(")[0]

    # # Create the .py file named after the function
    # filename = f"{func_name}.py"
    filename = f"gh_function.py"
    filename = os.path.join(path, filename)

    # content = concat_code(gh_code, summary, idea_file)
    summary_string = f'""" Summary:\n{summary}"""\n\n'
    with open(filename, "w") as f:
        f.write(summary_string)
        f.write(gh_code)
        print(f"Python script saved as {filename}")
    return gh_code

def get_obj_padding(dir):
    pad = 0
    for file in os.listdir(dir):
        if file.endswith(".obj"):
            pad += 1
    return str(pad).zfill(2)