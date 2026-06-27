import React from 'react';
import { Link, useParams } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import styles from './Blog.module.css';
import markdownStyles from './Markdown.module.css';
import { getBlogPost } from '../data/blog';
import { ChevronRight, Calendar, Clock, User, Tag } from '../components/icons';

export const BlogPost: React.FC = () => {
  const { slug } = useParams<{ slug: string }>();
  const post = slug ? getBlogPost(slug) : undefined;

  if (!post) {
    return (
      <div className={styles.page}>
        <Link to="/blog" className={styles.backLink}>
          <ChevronRight size={14} style={{ transform: 'rotate(180deg)' }} /> Back to blog
        </Link>
        <p className={styles.notFound}>That post could not be found.</p>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <nav className={styles.breadcrumb}>
        <Link to="/blog" className={styles.crumb}>
          Blog
        </Link>
        <ChevronRight size={13} />
        <span className={styles.crumbCurrent}>{post.title}</span>
      </nav>

      <article className={styles.article}>
        <header className={styles.articleHeader}>
          <div className={styles.tags}>
            {post.tags.map((t) => (
              <span key={t} className={styles.tag}>
                <Tag size={11} /> {t}
              </span>
            ))}
          </div>
          <h1 className={styles.articleTitle}>{post.title}</h1>
          <p className={styles.articleDesc}>{post.description}</p>
          <div className={styles.meta}>
            <span className={styles.metaItem}>
              <User size={13} />
              {post.author}
            </span>
            <span className={styles.metaItem}>
              <Calendar size={13} />
              {new Date(post.date).toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
              })}
            </span>
            <span className={styles.metaItem}>
              <Clock size={13} />
              {post.readingMinutes} min read
            </span>
          </div>
        </header>

        <div className={markdownStyles.markdown}>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{post.body}</ReactMarkdown>
        </div>
      </article>
    </div>
  );
};

export default BlogPost;
