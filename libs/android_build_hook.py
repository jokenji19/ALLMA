"""Normalize Buildozer's shell quotes when p4a receives an argv list.

Buildozer currently wraps manifest fragments in literal double quotes, although
p4a is launched without a shell. Do not patch installed tooling or templates.
"""


def before_apk_build(toolchain):
    prefixes=('--extra-manifest-application-arguments=','--extra-manifest-xml=')
    values=toolchain.args.unknown_args
    for index,value in enumerate(values):
        for prefix in prefixes:
            if value.startswith(prefix):
                fragment=value[len(prefix):]
                if len(fragment)>=2 and fragment[0]==fragment[-1]=='"':
                    fragment=fragment[1:-1].replace('\\"','"')
                    values[index]=prefix+fragment
