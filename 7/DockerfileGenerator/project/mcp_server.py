from mcp.server.fastmcp import FastMCP
import traceback
import shutil
import psutil

mcp = FastMCP("aushduaishd")


@mcp.tool()
def sum_numbers(numbers: list[float] | str | list[str]) -> float:
    """
    Sum all numbers in the provided input.

    :param numbers: Numbers to sum - can be a list of floats, a comma-separated string, or a list of strings
    :type numbers: list[float] | str | list[str]
    :raises ValueError: If input contains non-numeric values or is empty
    :raises TypeError: If input type is not supported
    :return: Sum of all numbers
    :rtype: float
    """
    try:
        if isinstance(numbers, str):
            if not numbers.strip():
                raise ValueError("Input string cannot be empty")
            number_list = [float(number.strip()) for number in numbers.split(",")]
        elif isinstance(numbers, list):
            if not numbers:
                raise ValueError("Input list cannot be empty")
            number_list = [float(number) for number in numbers]
        else:
            raise TypeError(f"Unsupported input type: {type(numbers)}")

        return sum(number_list)

    except (ValueError, TypeError):
        traceback.print_exc()
        raise


@mcp.tool()
def get_ssd_space() -> str:
    """
    Get available space information for all SSD drives in the system.

    :raises OSError: If there's an error accessing disk information.
    :raises ImportError: If required system modules are not available.
    :return: Formatted string with SSD space information.
    :rtype: str
    """

    try:
        ssd_info = []

        partitions = psutil.disk_partitions()

        for partition in partitions:
            try:
                usage = shutil.disk_usage(partition.mountpoint)

                total_gb = usage.total / (1024**3)
                free_gb = usage.free / (1024**3)
                used_gb = usage.used / (1024**3)
                usage_percent = (used_gb / total_gb) * 100

                drive_info = {
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "filesystem": partition.fstype,
                    "total_gb": round(total_gb, 2),
                    "used_gb": round(used_gb, 2),
                    "free_gb": round(free_gb, 2),
                    "usage_percent": round(usage_percent, 2),
                }

                ssd_info.append(drive_info)

            except (OSError, PermissionError):
                continue

        if not ssd_info:
            return "No accessible drives found."

        result = "SSD/Drive Space Information:\n"
        result += "=" * 50 + "\n"

        for drive in ssd_info:
            result += f"Device: {drive['device']}\n"
            result += f"Mount Point: {drive['mountpoint']}\n"
            result += f"Filesystem: {drive['filesystem']}\n"
            result += f"Total Space: {drive['total_gb']} GB\n"
            result += f"Used Space: {drive['used_gb']} GB ({drive['usage_percent']}%)\n"
            result += f"Free Space: {drive['free_gb']} GB\n"
            result += "-" * 30 + "\n"

        return result

    except (ImportError, OSError) as e:
        traceback.print_exc()
        return f"Error retrieving disk space information: {str(e)}"


@mcp.tool()
def get_memory_info() -> str:
    """
    Retrieves RAM memory information including free memory and top 2 memory-consuming processes.

    :return: Formatted string with memory information and top processes.
    :rtype: str
    :raises ImportError: If required modules are not available.
    :raises OSError: If system information cannot be accessed.
    """
    try:
        memory = psutil.virtual_memory()

        total_gb = memory.total / (1024**3)
        available_gb = memory.available / (1024**3)
        used_gb = memory.used / (1024**3)
        usage_percent = memory.percent

        processes = []
        for proc in psutil.process_iter(["pid", "name", "memory_info"]):
            try:
                memory_mb = proc.info["memory_info"].rss / (1024**2)
                processes.append(
                    {
                        "pid": proc.info["pid"],
                        "name": proc.info["name"],
                        "memory_mb": memory_mb,
                    }
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        top_processes = sorted(processes, key=lambda x: x["memory_mb"], reverse=True)[
            :2
        ]

        result = "RAM Memory Information:\n"
        result += "=" * 50 + "\n"
        result += f"Total RAM: {round(total_gb, 2)} GB\n"
        result += f"Used RAM: {round(used_gb, 2)} GB ({round(usage_percent, 2)}%)\n"
        result += f"Available RAM: {round(available_gb, 2)} GB\n"
        result += "\nTop 2 Memory-Consuming Processes:\n"
        result += "-" * 40 + "\n"

        for i, proc in enumerate(top_processes, 1):
            result += f"{i}. PID: {proc['pid']}\n"
            result += f"   Name: {proc['name']}\n"
            result += f"   Memory Usage: {round(proc['memory_mb'], 2)} MB\n"
            result += "-" * 30 + "\n"

        return result

    except (ImportError, OSError) as e:
        traceback.print_exc()
        return f"Error retrieving memory information: {str(e)}"


if __name__ == "__main__":
    mcp.run(transport="stdio")