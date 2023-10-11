# Shell Auto Completion
#
# https://www.baeldung.com/linux/compgen-command-usage
# https://www.baeldung.com/linux/shell-auto-completion
# 

function _opt() {
    # COMP_WORDS holds the command line incl. the latest one (can be ""):
    # opt.py ins<TAB><TAB> -> COMP_WORDS = ("opt.py" "ins")
    # opt.py install <TAB><TAB> -> COMP_WORDS = ("opt.py" "install" "")
    compWithoutLatest="${COMP_WORDS[@]:0:$COMP_CWORD}"
    latest="${COMP_WORDS[$COMP_CWORD]}"
    
    local commands=("install" "update" "remove" "desktop" "autocomplete" "path" "list" "alias")
    
    local options="-h --help --debug -y --yes"
    options="$options ${commands[@]}"
    
    # set program options as default
    local words="$options"

    # overwrite $words for command options
    local filesAllowed=false
    local command=""
    for e in $compWithoutLatest
    do
    
        case "${e}" in 
            install | update | remove | desktop | autocomplete | path | list | "alias")
                local installDir="/opt/.installer/"
                if [ -d $installDir ]; then
                    appdirs=($(find $installDir -mindepth 1 -maxdepth 1 -type d -printf '%f '))
                    words="-h --help ${appdirs[@]}"
                else
                    filesAllowed=true
                    words="-h --help"
                fi
                command=${e}
                ;;
            *)
                # check if command is available
                if [ "${command}" ]; then
                    filesAllowed=true

                    case "${command}" in 
                        install)
                            words="--no-path"
                            ;;
                        update)
                            words="--delete --keep"
                            ;;
                        remove)
                            words="-f --force --path-only --desktop-only"
                            ;;
                        desktop | autocomplete | list | alias)
                            words=""
                            ;;
                        path)
                            words="--link-name"
                            ;;
                    esac
                fi
        esac
    done
    

    if $filesAllowed ; then
       COMPREPLY=($(compgen -fd -W "$words" -- $latest))
    else
        COMPREPLY=($(compgen -W "$words" -- $latest))
    fi
    return 0
}

complete -F _opt opt.py
