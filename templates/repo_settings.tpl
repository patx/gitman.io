% rebase("base.tpl", title=repo["owner_username"] + "/" + repo["name"] + " settings", user=user, error=error, notice=notice)

<section class="repo-header slim">
  <div>
    % include("repo_fork_eyebrow.tpl")
    % include("repo_title.tpl", repo=repo)
    
    % include("repo_nav.tpl", repo=repo, commit_count=commit_count, issue_counts=issue_counts, pr_counts=pr_counts, star_count=star_count, is_starred=is_starred, is_owner=is_owner, can_maintain=can_maintain)
    
  </div>
</section>

<section class="panel">
  <h2>Description</h2>
  <form method="post">
    {{!csrf_field()}}
    <input type="hidden" name="action" value="save">
    <label>
      Repository description
      <input name="description" value="{{repo['description']}}" maxlength="500" placeholder="Repository description">
    </label>
    <button class="button" type="submit">Save description</button>
  </form>
</section>

<section class="panel">
  <h2>Contributors</h2>
  % if contributors:
    <ul class="clean-list">
      % for contributor in contributors:
        <li class="panel-heading">
          <span><a href="/{{contributor['username']}}">{{contributor["username"]}}</a> <span class="muted">added {{contributor["contributor_since"]}}</span></span>
          <form class="inline-form" method="post">
            {{!csrf_field()}}
            <input type="hidden" name="action" value="remove_contributor">
            <input type="hidden" name="user_id" value="{{contributor['id']}}">
            <button class="button secondary small" type="submit">Remove</button>
          </form>
        </li>
      % end
    </ul>
  % else:
    <p class="empty">No contributors yet.</p>
  % end
  <form method="post">
    {{!csrf_field()}}
    <input type="hidden" name="action" value="add_contributor">
    <label>
      Username
      <input name="username" value="{{contributor_username}}" autocomplete="off" placeholder="username">
    </label>
    <button class="button" type="submit">Add contributor</button>
  </form>
</section>

<section class="panel danger-zone">
  <h2>Delete repository</h2>
  <p>This permanently deletes the repository, its issues, pull requests, and Git data.</p>
  <form method="post">
    {{!csrf_field()}}
    <input type="hidden" name="action" value="delete">
    <label>
      Type {{repo["name"]}} to confirm
      <input name="confirm_name" autocomplete="off">
    </label>
    <button class="button danger" type="submit">Delete repository</button>
  </form>
</section>
