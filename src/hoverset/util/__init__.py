import re

version_types = {
    "rc": "Release Candidate",
    "b": "Beta release",
    "a": "Alpha release",
    "dev": "Development release",
    "post": "Post Release",
}


def version_description(version):
    search = re.search(
        r"(?P<version>\d+\.\d+\.\d+)(?P<type>[A-Za-z]+)(?P<number>\d+)",
        version
    )

    if search and len(search.groups()) == 3:
        ver, r_type, num = (
            search.group("version"),
            search.group("type"),
            search.group("number")
        )
        return f"{ver} {version_types.get(r_type, r_type)} {num}"
    return version
