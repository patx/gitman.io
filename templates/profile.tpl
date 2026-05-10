% profile_name = profile_user["display_name"] or profile_user["username"]
% rebase("base.tpl", title=profile_name, user=user, error=error, notice=notice)

<section class="profile-header">
  <h1>
  % if not profile_user["display_name"]:
    {{profile_name}}
  % else:
    {{profile_name}} <small>(@{{profile_user["username"]}})</small>
  % end
  </h1>
  <p class="muted"><small>
    Joined {{profile_user["created_at"]}}
    % if is_self:
      <a class="button-link" href="/settings/profile">Edit profile</a> &middot; <a class="button-link" href="/logout">Log out</a>
    % end
  </small></p>
  % if profile_user["bio"]:
    <p>{{!render_markdown_links(profile_user["bio"])}}</p>
  % end
  % if profile_user["website"]:
    <p><a href="{{profile_user['website']}}" rel="nofollow">{{profile_user["website"]}}</a></p>
  % end
</section>

<section class="panel">
  <div class="panel-heading">
    <h2>Repositories</h2>
    <nav class="tabs">
      <a class="{{'active' if active_tab == 'owned' else ''}}" href="/{{profile_user['username']}}">Owned ({{owned_count}})</a>
      <a class="{{'active' if active_tab == 'stars' else ''}}" href="/{{profile_user['username']}}?tab=stars">Starred ({{starred_count}})</a>
    </nav>
  </div>
  % if repos:
    <div class="repo-list" data-paginated-list>
      % for repo in repos:
        <div>
          <a href="/{{repo['owner_username']}}/{{repo['name']}}">
            <strong>{{repo["owner_username"]}}/{{repo["name"]}}</strong></a>
            <br>
            {{!render_markdown_links(repo["description"]) or "No description yet."}}
            <br>
            <small>Updated {{repo["updated_at"]}} · {{repo["star_count"]}} stars</small>
        </div>
      % end
    </div>
      % include("pagination.tpl", pagination=pagination)
  % else:
    % if pagination["page"] > 1:
      <p class="empty">No repositories on this page.</p>
    % else:
      <p class="empty">{{"No starred repositories yet." if active_tab == "stars" else "No repositories yet."}}</p>
    % end
    % include("pagination.tpl", pagination=pagination)
  % end
</section>
