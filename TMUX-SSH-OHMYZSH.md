# Fixing Font and Icon Rendering in Tmux (with Oh My Zsh + Powerlevel10k)
                                                       
If your Powerlevel10k icons or Nerd Font glyphs appear as garbled characters (like `_ _ _`) inside `tmux` but look fine in your regular terminal, follow these steps to fix the encoding and terminal configuration.
                                                                                                                                                                                                                               
## 1. Configure UTF-8 Locale in `.zshrc`
                                                       
Tmux needs to know it should operate in UTF-8 mode. This is driven by your environment's locale variables. Ensure these are explicitly exported in your `~/.zshrc`:
                                                       
```zsh                   
# Ensure the locale is set to a UTF-8 aware one
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8                                                                                                                                                                                                      
```
                                                       
*Note: Without these, tmux might default to a non-UTF-8 'C' locale, which doesn't support the special glyphs used by Powerlevel10k.*
                                                                                                                                                                                                                               
## 2. Conditionalize `$TERM` Overrides
                                                       
Many users manually export `TERM=xterm-256color` in their `.zshrc`. However, inside `tmux`, the `$TERM` should ideally be `screen-256color` or `tmux-256color`. Overwriting it inside `tmux` can break rendering.
                                                       
Change your `TERM` export in `~/.zshrc` to:                                                                    
                                                       
```zsh
# Only set TERM to xterm-256color if we are NOT inside a tmux session
[[ -z "$TMUX" ]] && export TERM=xterm-256color     
```
                                                                                                               
## 3. Configure `~/.tmux.conf` for Colors and UTF-8
                                                       
Create or update your `~/.tmux.conf` to ensure it uses a 256-color terminal and knows your default shell:
                                                       
```tmux
# Use 256 colors for proper Powerlevel10k theme support
set -g default-terminal "screen-256color"
                                                       
# Ensure tmux uses your preferred shell (zsh)
set -g default-shell /bin/zsh                          
```
                                                                                                               
## 4. SSH Environment Forwarding (Important for Remote)
                                                       
If you are SSH-ing into a machine and then running `tmux`, your local machine's locale might not be forwarded. 
                                                       
- **On your local machine** (`~/.ssh/config`):
  ```ssh
  Host *                                            
      SendEnv LANG LC_*
  ```                
- **On the remote server** (`/etc/ssh/sshd_config`):
  ```ssh
  AcceptEnv LANG LC_*        
  ```
                                                                                                               
## 5. Restart and Force UTF-8
                                                       
After making these changes, you must fully restart the `tmux` server.
                                                       
1.  **Kill the current server:**
    ```bash                      
    tmux kill-server
    ```            
2.  **Source your shell config:**
    ```bash                           
    source ~/.zshrc                                                                                            
    ```    
3.  **Start tmux with the `-u` flag:**
    The `-u` flag forces `tmux` to use UTF-8 even if it thinks the environment doesn't support it.
    ```bash                                                                                                                                                                                                                    
    tmux -u
    ```