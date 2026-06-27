import React from 'react';
import { Link } from 'react-router-dom';
import styles from './Blog.module.css';
import { BLOG_POSTS } from '../data/blog';
import { BookOpen, Calendar, Clock, Tag, ArrowUpRight } from '../components/icons';

export const Blog: React.FC = () => {
  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.titleRow}>
          <BookOpen size={22} className={styles.titleIcon} />
          <h1 className={styles.title}>Blog</h1>
        </div>
        <p className={styles.subtitle}>
          Notes on AI agents, self-improving memory, and the systems that make
          agents learn from their own runs.
        </p>
      </header>

      <div className={styles.list}>
        {BLOG_POSTS.map((post) => (
          <Link key={post.slug} to={`/blog/${post.slug}`} className={styles.cardLink}>
            <article className={styles.card}>
              <div className={styles.cardBody}>
                <div className={styles.tags}>
                  {post.tags.map((t) => (
                    <span key={t} className={styles.tag}>
                      <Tag size={11} /> {t}
                    </span>
                  ))}
                </div>
                <h2 className={styles.cardTitle}>{post.title}</h2>
                <p className={styles.cardDesc}>{post.description}</p>
                <div className={styles.meta}>
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
                  <span className={styles.author}>{post.author}</span>
                </div>
              </div>
              <span className={styles.readMore}>
                Read <ArrowUpRight size={15} />
              </span>
            </article>
          </Link>
        ))}
      </div>
    </div>
  );
};

export default Blog;
