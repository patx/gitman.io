% rebase("base.tpl", title=repo["owner_username"] + "/" + repo["name"], user=user, error=error, notice=notice)

<section class="repo-header">
  <div>
    % include("repo_fork_eyebrow.tpl")
    % include("repo_title.tpl", repo=repo)

    % include("repo_nav.tpl", repo=repo, commit_count=commit_count, issue_counts=issue_counts, pr_counts=pr_counts, star_count=star_count, is_starred=is_starred, is_owner=is_owner, can_maintain=can_maintain)

    <p>{{!render_markdown_links(repo["description"]) or "No description yet."}}</p>
  </div>
  <div class="clone-box">
    <code>$ git clone {{clone_url}}</code>
  </div>
</section>

<section class="panel">
  % if readme_html is not None:
    % if readme_truncated:
      <p class="notice">README preview truncated. Use the source or raw view for the full file.</p>
    % end
    <div class="readme markdown-body">{{!readme_html}}</div>
  % elif readme is not None:
    % if readme_truncated:
      <p class="notice">README preview truncated. Use the source or raw view for the full file.</p>
    % end
    <pre class="readme">{{readme}}</pre>
  % else:
    <div class="empty">
      % if commit_count == 0:
        <p>This repository is empty.</p>
        <h3>Start with a fresh checkout</h3>
        <pre>git clone {{clone_url}}
cd {{repo["name"]}}
echo "# {{repo["name"]}}" &gt; README.md
git add README.md
git commit -m "Initial commit"
git push -u origin main</pre>
        <h3>Push an existing local Git repo</h3>
        <pre>cd /path/to/existing-repo
git remote add origin {{clone_url}}
git push -u origin HEAD:main</pre>
        <p class="muted">Push will ask for the repository owner's or a contributor's username and password.</p>
      % else:
        <p>This repository has no README.</p>
        <pre>echo "# {{repo["name"]}}" &gt; README.md
git add README.md
git commit -m "Add README"
git push</pre>
      % end
    </div>
  % end
</section>
