#####################################################
# cspm_agent.py
# 
# Agent to perform tenancy security evaluation 
# based on security profile provided to the LLM.
#
# npotlapa@alumni.princeton.edu
#####################################################

import os
import socket
import sys
import subprocess
import time
from pathlib import Path

import aisuite as ai
from aisuite.mcp import MCPClient

from dotenv import load_dotenv

from mcp_tools import check_ssh_connectivity, scan_ports

from llm_functions import print_llm_response, print_intermediate_msgs, llm_token_usage

# Initialize env variables
#
load_dotenv()
if not os.getenv("ANTHROPIC_API_KEY"):
    raise ValueError("ANTHROPIC_API_KEY env variable not set")
ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")

if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY env variable not set")
OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")

UVX_PATH: str | None = os.getenv("UVX_PATH", "uvx")

# models to use
#
models = ["anthropic:claude-sonnet-4-6", "openai:gpt-4.1"]

# print colors
#
RED = "\033[31m"
BLUE = "\033[34m"
RESET = "\033[0m"

def run_security_prompt(label: str, prompt: str, tools, model: str, max_turns: int = 15):
    print(f"{RED}={'='*60}{RESET}")
    print(f"{RED}STEP: {label}{RESET}")
    print(f"{prompt}")
    messages = [{"role": "system", "content": system_str},
                {"role": "user", "content": prompt}]
    response = client.chat.completions.create(
                model=model, 
                messages=messages, 
                tools=tools, 
                max_turns=max_turns)
    print(f"{RED}={RESET}"*60)
    print(f"{RED}RESULTS: {RESET}")
    print(f"{RED}={RESET}"*60)
    print(f"{BLUE}")
    print(response.choices[0].message.content)
    print(f"{RESET}")
    print(f"{RED}={RESET}"*60)
    return response

# Initialize mcp client and mcp memory 
#
try:
    mcp_client = MCPClient(
            command=UVX_PATH,
            args=["oracle.oci-api-mcp-server@latest"]
            )
except Exception as e:
    raise RuntimeError(f"Failed to connect to OCI MCP server: {e}") from e

memory_file = os.path.join(os.getcwd(), "oci_security_skills.jsonl")
file_path = Path(memory_file)
if file_path.exists() and file_path.is_file():
    file_path.unlink()
    print("Deleted existing file: ")
else:
    print("Memory file created: ")
print(memory_file)

try:
    memory_mcp = MCPClient(
            command="npx",
            args=["-q", "-y", "@modelcontextprotocol/server-memory"],
            env ={"MEMORY_FILE_PATH": memory_file},
            name="memory"
            )
except Exception as e:
    raise RuntimeError(f"Failed to connect to MCP server memory: {e}") from e

# Print status of the MCP client
print(f"Connected to MCP server: {mcp_client}")
print(f"Connected to MCP memory server: {memory_mcp}")

custom_tools = [check_ssh_connectivity, scan_ports]
mcp_tools = mcp_client.get_callable_tools()
all_tools = mcp_tools + memory_mcp.get_callable_tools() + custom_tools 

# Create aisuite client
#
client = ai.Client()

# Create OCI security profile file
#
system_str = """
You are a security expert with deep experience in security of Oracle cloud infrastructure. Your job is to evaluate security of Oracle Cloud Infrastructure (OCI) tenancy and resources, and provide security recommendations
"""
messages = [
          {"role":"system","content": system_str},
          {"role":"user", "content":"""
           Below is the OCI tenancy security evaluation profile. Store this security evaluation profile in memory:

           **Objective**
           Perform security evaluation of an OCI tenancy using all the security checks provided. For each security check, assign 
           security criticality to the finding.  

           **Security checks**
           List of all security checks to perform on the OCI tenancy. They are categorized into security checks for compute, storage, 
           networking and IAM. 
           
           ***Compute security checks***
            - Verify whether an OCI instance is open to network access from the Internet. Use the VCN Security Lists and NSGs in VCN subnet to execute this check 
            - Check SSH connectivity of running instancs using their IP address
            - Scan network ports of running compute instance using their IP address. Check whether any ports are open to and pose 
           
           ***Storage security checks***
            - Check object storage buckets do not have public access. 
            - Check for Buckets with encryption using Oracle-managed keys instead of customer-managed keys. Using Customer-managed keys is recommended for security.
            - Check for Buckets without versioning enabled

           ***Networking security checks***
            - Check for VCN security list with 0.0.0.0/0 ingress on security sensitive ports such as 22, 3389 etc
            - Check for NSGs with 0.0.0.0/0 ingress on security sensitive ports such as 22. 3389 etc
            - Check for no Service Gateway in VCN

           ***IAM security checks***
            - MFA is enabled for all IAM users 
            - Administrators IAM group does not have more than 3 users
            - API keys of IAM users are not older than 90 days
            - Password of IAM users enforces password complexity rules.  

           **Tools**
           Below are tools available to implement the security checks
           - check_ssh_connectivity(IP_ADDRESS): Check SSH connectivity to compute instance. IP_ADDRESS is public IP address of the instance.
           - scan_ports(IP_ADDRESS): Scans network ports on compute instance to determine their status (open, closed). IP_ADDRESS is the IP address of the instance 
           
           Store the profile in memory. Summarize the profile.
           """
           }
        ]
try: 
    response = client.chat.completions.create(
            model=models[0],
            messages=messages,
            tools=all_tools,
            max_turns=5
            )

    print(f"{RED}={RESET}"*60)
    print(f"{RED}OCI TENANCY SECURITY PROFILE{RESET}")
    print(f"{RED}={RESET}"*60)
    print(f"{BLUE}")
    print(response.choices[0].message.content)
    print(f"{RESET}")
    print(f"{RED}={RESET}"*60)

    # Print token usage
    llm_token_usage(response)

    # Make tenancy security queries
    #
    security_prompts = {
            "compute":"Run security evaluation of OCI tenancy. Run all the compute security checks from the security profile stored in memory. List all the instances in the compartment and print their IP addresses",
            "storage":"Run security evaluation of OCI tenancy. Run all the storage security checks from the security profile stored in memory.",
            "networking":"Run security evaluation of OCI tenancy. Run all the networking security checks from the security profile stored in memory. List all the VCNs in the teanncy",
            "iam":"Run security evaluation of OCI tenancy. Run all the iam security checks from the security profile stored in memory. List all the IAM users in the tenancy"
    }

    for service, prompt in security_prompts.items():
        label = f"{service} security evaluation"
        model = models[0]
        tools = all_tools
        max_turns = 15
        response = run_security_prompt(label, prompt, tools, model, max_turns)
        llm_token_usage(response)

finally:
    # Close MCP connections
    #
    mcp_client.close()
    memory_mcp.close()
    print("MCP connection closed")



