#!/bin/bash
# wait-for-it.sh - Wait for service to be available

TIMEOUT=15
QUIET=0

usage() {
    cat << USAGE >&2
Usage:
    $0 host:port [-t timeout] [-- command args]
    -q | --quiet                        Do not output any status messages
    -t TIMEOUT | --timeout=timeout      Timeout in seconds, zero for no timeout
    -- COMMAND ARGS                     Execute command with args after the test finishes
USAGE
    exit 1
}

wait_for() {
    if [[ $TIMEOUT -gt 0 ]]; then
        echo "Waiting $TIMEOUT seconds for $HOST:$PORT..."
    else
        echo "Waiting for $HOST:$PORT without a timeout..."
    fi

    START_TIME=$(date +%s)
    while :
    do
        if nc -z "$HOST" "$PORT"; then
            END_TIME=$(date +%s)
            ELAPSED=$((END_TIME - START_TIME))
            if [[ $QUIET -ne 1 ]]; then
                echo "$HOST:$PORT is available after $ELAPSED seconds"
            fi
            break
        fi
        sleep 1

        if [[ $TIMEOUT -gt 0 ]]; then
            CURRENT_TIME=$(date +%s)
            ELAPSED=$((CURRENT_TIME - START_TIME))
            if [[ $ELAPSED -ge $TIMEOUT ]]; then
                echo "Timeout occurred after waiting $TIMEOUT seconds for $HOST:$PORT"
                exit 1
            fi
        fi
    done
}

while [[ $# -gt 0 ]]
do
    case "$1" in
        *:* )
        HOSTPORT=(${1//:/ })
        HOST=${HOSTPORT[0]}
        PORT=${HOSTPORT[1]}
        shift 1
        ;;
        -q | --quiet)
        QUIET=1
        shift 1
        ;;
        -t)
        TIMEOUT="$2"
        if [[ $TIMEOUT == "" ]]; then break; fi
        shift 2
        ;;
        --timeout=*)
        TIMEOUT="${1#*=}"
        shift 1
        ;;
        --)
        shift
        CLI=("$@")
        break
        ;;
        --help)
        usage
        ;;
        *)
        echo "Unknown argument: $1"
        usage
        ;;
    esac
done

if [[ "$HOST" == "" || "$PORT" == "" ]]; then
    echo "Error: you need to provide a host and port to test."
    usage
fi

wait_for

if [[ -n "${CLI[@]}" ]]; then
    exec "${CLI[@]}"
fi

exit 0
