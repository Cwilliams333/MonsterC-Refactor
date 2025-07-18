#!/usr/bin/env bash
#
# bert_tool.sh  --  run commands on a bertta box & pull files back
#
#   Usage examples
#   --------------
#   export FUSIONPW='fusionproject'        # or pass --pw
#
#   # 1) single quick command
#   ./bert_tool.sh --bert 18 \
#                  --cmd  "bash /home/fusion/make_csv.sh" \
#                  --get  "/home/fusion/out.csv"
#
#   # 2) many commands via JSON array, two files to fetch
#   ./bert_tool.sh --bert 25 \
#                  --cmd-json '["echo hello","uptime","bash make.sh"]' \
#                  --get "/home/fusion/a.log" --get "/home/fusion/b.log"
#

set -euo pipefail

############  editable constants  ############
JUMP=ubuntu@52.54.110.136
SSH_OPTS=(
  -o StrictHostKeyChecking=accept-new
  -o UserKnownHostsFile=/dev/null          # skip known_hosts noise
)
##############################################

die() { echo "❌  $*" >&2; exit 1; }

# --- parse args -------------------------------------------------------
BERT=   PW=${FUSIONPW:-}  CMDS=()  GET_PATHS=()

while [[ $# -gt 0 ]]; do
  case $1 in
    -b|--bert)   BERT=$2; shift 2;;
    --pw)        PW=$2; shift 2;;
    --cmd)       CMDS+=("$2"); shift 2;;
    --cmd-json)  mapfile -t CMDS < <( jq -r '.[]' <<<"$2" ); shift 2;;
    --get)       GET_PATHS+=("$2"); shift 2;;
    -h|--help)   grep '^#' "$0" | sed 's/^#//'; exit 0;;
    *)           die "Unknown arg $1";;
  esac
done

[[ $BERT =~ ^(17|18|24|25|56)$ ]] || die "Invalid bert number"
[[ ${#CMDS[@]} -gt 0 ]]            || die "No commands supplied"
[[ -n $PW ]]                       || die "Password (--pw or \$FUSIONPW) required"

PORT="450$BERT"
DEST="fusion@127.0.0.1"

# --- helper to run over sshpass+ProxyJump -----------------------------
ssh_fusion() {
  sshpass -p "$PW" ssh "${SSH_OPTS[@]}"                    \
    -o ProxyJump="$JUMP"                                   \
    -p "$PORT"                                             \
    "$DEST" "$@"
}

scp_fusion() {
  sshpass -p "$PW" scp "${SSH_OPTS[@]}"                    \
    -o ProxyJump="$JUMP"                                   \
    -P "$PORT"                                             \
    "$DEST:$1" .
}

# --- execute commands -------------------------------------------------
echo "▶ running on bertta$BERT (port $PORT)..."
for cmd in "${CMDS[@]}"; do
  echo "   $cmd"
  ssh_fusion -- bash -c "$cmd"
done

# --- fetch files ------------------------------------------------------
for remote in "${GET_PATHS[@]}"; do
  echo "⬇  $remote → ./$(basename "$remote")"
  scp_fusion "$remote"
done

echo "✅  finished OK"
